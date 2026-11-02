"""训练数据质检：识别常见数据质量问题并给出清洗结果。

所有检查函数接收 DataFrame、返回问题行的索引集合，
这样既能单独测试，也能让 clean() 按统一索引删除。
"""
import re
from collections import Counter
from difflib import SequenceMatcher

import pandas as pd

REQUIRED_COLUMNS = ("text", "label")
MIN_TEXT_LEN = 3
NEAR_DUP_RATIO = 0.92
NEAR_DUP_LEN_GAP = 0.15
IMBALANCE_RATIO = 0.10

ISSUE_NAMES = {
    "missing_text": "文本为空",
    "too_short": "文本过短",
    "exact_duplicate": "完全重复",
    "near_duplicate": "近似重复",
    "label_conflict": "标签冲突",
    "invalid_label": "标签非法",
}

_WS_RE = re.compile(r"\s+")


def _texts(df):
    return df["text"].fillna("").astype(str).str.strip()


def _labels(df):
    return df["label"].fillna("").astype(str).str.strip()


def check_missing_text(df):
    """文本为空或只有空白字符。"""
    texts = _texts(df)
    return set(texts[texts == ""].index)


def check_too_short(df):
    """去空白后长度小于 MIN_TEXT_LEN，这类样本对模型几乎没有信息量。"""
    texts = _texts(df)
    return set(texts[(texts != "") & (texts.str.len() < MIN_TEXT_LEN)].index)


def check_exact_duplicate(df, exclude=None):
    """文本完全一致，保留首次出现，其余判重复。

    exclude 里的行已被其他检查判定，不再重复计入。
    """
    exclude = exclude or set()
    texts = _texts(df)
    seen = set()
    dup = set()
    for idx, text in texts.items():
        if text == "" or idx in exclude:
            continue
        if text in seen:
            dup.add(idx)
        else:
            seen.add(text)
    return dup


def check_near_duplicate(df, exclude):
    """按长度排序后两两比对，长度差过大就跳过，相似度超阈值判重复。

    复杂度是 O(n^2)，但先按长度剪枝，万条以内可接受；
    数据量再大应换成 SimHash 或 MinHash。
    """
    texts = _texts(df)
    items = [(idx, text) for idx, text in texts.items()
             if text and idx not in exclude]
    items.sort(key=lambda pair: len(pair[1]))

    dup = set()
    for a in range(len(items)):
        idx_a, text_a = items[a]
        if idx_a in dup:
            continue
        limit = len(text_a) + max(2, int(len(text_a) * NEAR_DUP_LEN_GAP))
        for b in range(a + 1, len(items)):
            idx_b, text_b = items[b]
            if len(text_b) > limit:
                break
            if idx_b in dup:
                continue
            if SequenceMatcher(None, text_a, text_b).ratio() >= NEAR_DUP_RATIO:
                dup.add(idx_b)
    return dup


def check_label_conflict(df):
    """同一条文本被打上多个标签，保留票数最多的标签，其余行判冲突。"""
    texts = _texts(df)
    labels = _labels(df)
    groups = {}
    for idx in df.index:
        text = texts[idx]
        if text == "":
            continue
        groups.setdefault(text, []).append(idx)

    conflict = set()
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        votes = Counter(labels[i] for i in idxs)
        if len(votes) <= 1:
            continue
        keep = votes.most_common(1)[0][0]
        for i in idxs:
            if labels[i] != keep:
                conflict.add(i)
    return conflict


def check_invalid_label(df):
    """标签为空，或超过 20 个字符（多数场景下标签应是短词）。"""
    labels = _labels(df)
    bad = labels[(labels == "") | (labels.str.len() > 20)]
    return set(bad.index)


def label_distribution(df):
    labels = _labels(df)
    labels = labels[labels != ""]
    return dict(Counter(labels))


def is_imbalanced(dist, total):
    """最小类别占比低于 10% 视为不平衡，样本少于 10 条时不判定。"""
    if total < 10 or len(dist) < 2:
        return False
    minority = min(dist.values()) / total
    return minority < IMBALANCE_RATIO


def _run_checks(df):
    issues = {}
    issues["missing_text"] = check_missing_text(df)
    issues["too_short"] = check_too_short(df)
    issues["label_conflict"] = check_label_conflict(df)
    issues["invalid_label"] = check_invalid_label(df)
    exclude = set(issues["label_conflict"]) | set(issues["invalid_label"])
    issues["exact_duplicate"] = check_exact_duplicate(df, exclude)
    issues["near_duplicate"] = check_near_duplicate(
        df, exclude | set(issues["exact_duplicate"]))
    return issues


def score_of(issues, total, imbalanced):
    """问题行占比每 1% 扣 3 分，类别不平衡额外扣 10 分。

    用占比而不是绝对条数，是为了让不同规模的数据集分数可比：
    500 条里有 50 条问题和 5 万条里有 5000 条问题，严重程度是一样的。
    """
    bad = set()
    for rows in issues.values():
        bad |= rows
    ratio = len(bad) / total if total else 0
    score = 100 - ratio * 300
    if imbalanced:
        score -= 10
    return max(0, int(round(score)))


def level_of(score):
    if score >= 85:
        return "良好"
    if score >= 70:
        return "中等"
    if score >= 50:
        return "较差"
    return "严重"


def validate_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("缺少必需列：" + "、".join(missing))


def _build_report(df, issues):
    total = len(df)
    bad = set()
    for rows in issues.values():
        bad |= rows
    dist = label_distribution(df)
    imbalanced = is_imbalanced(dist, total)
    score = score_of(issues, total, imbalanced)

    return {
        "total": total,
        "problem_rows": len(bad),
        "clean_rows": total - len(bad),
        "score": score,
        "level": level_of(score),
        "imbalanced": imbalanced,
        "label_distribution": dist,
        "issues": [
            {
                "key": key,
                "name": ISSUE_NAMES[key],
                "count": len(issues[key]),
                "rows": sorted(int(i) for i in issues[key])[:20],
            }
            for key in ISSUE_NAMES
        ],
        "issue_names": ISSUE_NAMES,
    }


def inspect(df):
    """返回质量报告，不修改原数据。"""
    validate_columns(df)
    return _build_report(df, _run_checks(df))


def clean(df):
    """按检查结果删除问题行，返回清洗后的数据和报告。"""
    validate_columns(df)
    issues = _run_checks(df)
    bad = set()
    for rows in issues.values():
        bad |= rows
    kept = df.drop(index=[i for i in bad if i in df.index]).reset_index(drop=True)
    return kept, _build_report(df, issues)
