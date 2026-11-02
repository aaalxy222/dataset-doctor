"""生成带典型质量问题的示例数据集，用于演示和测试。

注入的问题：空文本 6 条、超短 8 条、完全重复 12 条、
近似重复 10 条、标签冲突 5 条，且类别分布严重不平衡。
"""
import random

import pandas as pd

random.seed(20261102)

SUBJ = ["这个产品", "这款耳机", "这台机器", "这个服务", "这次的体验",
        "这家店", "这个方案", "这本教材"]
GOOD = ["很好用", "超出预期", "质量不错", "性价比很高",
        "用起来顺手", "细节做得到位", "值得回购", "比想象中好"]
BAD = ["很失望", "做工粗糙", "完全不值", "客服不理人",
       "用了两天就坏", "包装破损", "发货太慢", "和描述不符"]
NEUTRAL = ["还行吧", "中规中矩", "没什么特别的",
           "一般般", "看个人需求", "不好也不坏"]
DETAIL = ["音质清晰", "续航够用", "手感不错", "包装精致",
          "客服回复快", "价格公道", "做工扎实", "外观简约"]
TAIL = ["下次还买", "推荐给朋友", "物流也快", "包装很用心",
        "希望改进", "整体满意", "会再考虑", "先观察一阵"]


def _make_unique(count, words):
    seen = set()
    texts = []
    while len(texts) < count:
        text = (f"{random.choice(SUBJ)}{random.choice(words)}"
                f"{random.choice(DETAIL)}，{random.choice(TAIL)}")
        if text not in seen:
            seen.add(text)
            texts.append(text)
    return texts


def build():
    rows = []
    for text in _make_unique(400, GOOD):
        rows.append({"text": text, "label": "正向"})
    for text in _make_unique(80, BAD):
        rows.append({"text": text, "label": "负向"})
    for text in _make_unique(20, NEUTRAL):
        rows.append({"text": text, "label": "中性"})

    # 完全重复：原样复制 12 条
    for row in random.sample(rows, 12):
        rows.append(dict(row))

    # 近似重复：句末加标点，文本几乎一样
    for row in random.sample(rows[:400], 10):
        rows.append({"text": row["text"] + "。", "label": row["label"]})

    # 标签冲突：同一条文本换一个标签
    for row in random.sample(rows[:400], 5):
        wrong = random.choice(["负向", "中性"])
        rows.append({"text": row["text"], "label": wrong})

    # 空文本：标签仍在，文本为空
    for _ in range(6):
        rows.append({"text": "", "label": "正向"})

    # 超短文本：一两个字，没有信息量
    for word in ["好", "差", "行", "不错", "不行", "可以", "烂", "棒"]:
        rows.append({"text": word, "label": random.choice(["正向", "负向"])})

    random.shuffle(rows)
    return pd.DataFrame(rows, columns=["text", "label"])


if __name__ == "__main__":
    df = build()
    df.to_csv("data/sample_dirty.csv", index=False, encoding="utf-8-sig")
    print(f"已生成 {len(df)} 条，标签分布：{df['label'].value_counts().to_dict()}")
