import pandas as pd
import pytest

from inspector import (
    check_exact_duplicate,
    check_invalid_label,
    check_label_conflict,
    check_missing_text,
    check_near_duplicate,
    check_too_short,
    clean,
    inspect,
    is_imbalanced,
    validate_columns,
)


def frame(rows):
    return pd.DataFrame(rows, columns=["text", "label"])


def test_missing_text_finds_blank_and_whitespace():
    df = frame([["", "正向"], ["   ", "负向"], ["正常文本", "正向"]])
    assert check_missing_text(df) == {0, 1}


def test_too_short_ignores_blank_rows():
    df = frame([["", "正向"], ["好", "正向"], ["还行吧", "负向"]])
    assert check_too_short(df) == {1}


def test_exact_duplicate_keeps_first_occurrence():
    df = frame([["同一句话", "正向"], ["别的", "负向"], ["同一句话", "正向"]])
    assert check_exact_duplicate(df) == {2}


def test_exact_duplicate_skips_excluded_rows():
    df = frame([["同一句话", "正向"], ["同一句话", "负向"]])
    assert check_exact_duplicate(df, exclude={0, 1}) == set()


def test_near_duplicate_handles_punctuation_only_change():
    df = frame([["这个产品很好用", "正向"], ["这个产品很好用。", "正向"], ["完全无关的另一段内容", "负向"]])
    assert 1 in check_near_duplicate(df, set())


def test_near_duplicate_ignores_short_and_unrelated():
    df = frame([["好", "正向"], ["差", "负向"], ["今天天气不错", "中性"]])
    assert check_near_duplicate(df, set()) == set()


def test_label_conflict_keeps_majority_label():
    df = frame([
        ["同一句话", "正向"],
        ["同一句话", "正向"],
        ["同一句话", "负向"],
    ])
    assert check_label_conflict(df) == {2}


def test_invalid_label_catches_empty_and_overlong():
    df = frame([["文本一", ""], ["文本二", "这是一个特别特别特别特别长的标签名称超过了长度限制"]])
    assert check_invalid_label(df) == {0, 1}


def test_imbalance_detects_rare_class():
    df = frame([["文本", "正向"]] * 95 + [["文本", "负向"]] * 5)
    assert is_imbalanced({"正向": 95, "负向": 5}, 100) is True


def test_imbalance_skips_small_datasets():
    df = frame([["文本", "正向"], ["文本", "负向"]])
    assert is_imbalanced({"正向": 1, "负向": 1}, 2) is False


def test_inspect_clean_dataset_scores_full_marks():
    texts = [
        "物流速度比预计快了两天", "客服耐心解答了退换货流程",
        "包装盒有点压扁但机器没坏", "价格比线下门店便宜不少",
        "说明书图文清晰上手很快", "颜色和详情页展示的一致",
        "续航表现符合宣传数据", "按键手感偏硬需要适应",
        "送的数据线做工一般", "开机速度比旧机器快很多",
        "噪音控制得比预期好", "安装师傅上门很准时",
        "售后电话响应速度快", "配件齐全没有缺件",
        "系统界面简洁容易上手", "重量控制得还可以",
        "屏幕在阳光下看得清", "充电速度比较满意",
        "外壳材质摸着有质感", "整体性价比在同价位算高",
    ]
    report = inspect(frame([[t, "正向"] for t in texts]))
    assert report["score"] == 100
    assert report["problem_rows"] == 0
    assert report["level"] == "良好"


def test_inspect_reports_expected_keys():
    report = inspect(frame([["正常文本内容", "正向"], ["", "负向"]]))
    assert {"total", "score", "issues", "label_distribution"} <= report.keys()
    assert [i["key"] for i in report["issues"]] == [
        "missing_text", "too_short", "exact_duplicate",
        "near_duplicate", "label_conflict", "invalid_label",
    ]


def test_clean_removes_all_problem_rows():
    df = frame([
        ["", "正向"],
        ["好", "正向"],
        ["正常的一条内容", "正向"],
        ["正常的一条内容", "正向"],
        ["另一条完全正常的内容", "负向"],
    ])
    cleaned, report = clean(df)
    assert report["problem_rows"] == 3
    assert len(cleaned) == 2
    assert cleaned["text"].tolist() == ["正常的一条内容", "另一条完全正常的内容"]


def test_validate_columns_rejects_missing_label():
    with pytest.raises(ValueError):
        validate_columns(pd.DataFrame({"text": ["a"]}))
