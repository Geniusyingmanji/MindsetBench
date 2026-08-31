"""Mindset 迁移 Bench 判分器。

用法：from grade import grade_item; grade_item(item, model_output) -> (bool, parsed)
约定：被测模型最后一行输出 "ANSWER: <答案>"；多段式答案用分号/逗号分隔。
"""
import re
from fractions import Fraction

_SEP = re.compile(r"[;；,，]")


def extract_answer(text: str) -> str:
    """取最后一个 ANSWER: 标记后的内容；没有标记则取最后一个非空行。"""
    matches = re.findall(r"ANSWER\s*[:：]\s*(.+)", text, flags=re.IGNORECASE)
    if matches:
        return matches[-1].strip()
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    return lines[-1] if lines else ""


def _to_number(s: str):
    s = s.strip().rstrip("。.").replace("％", "%")
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    try:
        v = float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", s)
        if not m:
            return None
        v = float(m.group())
    return v / 100 * 100 if not pct else v  # 百分号仅剥掉符号，数值口径与题面一致


def _num_eq(pred: float, gold: float, tol) -> bool:
    if tol is None:
        if float(gold).is_integer():
            tol = 1e-9  # 整数答案：精确匹配
        else:
            tol = max(abs(gold) * 5e-3, 5e-3)  # 小数答案：默认相对 0.5%
    elif tol == 0:
        tol = 1e-9
    return abs(pred - gold) <= tol


def _part_eq(pred: str, gold: str, tol) -> bool:
    pred, gold = pred.strip(), gold.strip()
    gp, pp = _to_number(gold), _to_number(pred)
    if gp is not None and re.fullmatch(r"-?[\d./%eE+-]+", gold.rstrip("%")):
        return pp is not None and _num_eq(pp, gp, tol)
    # 文本部分：忽略大小写与空白；单字母选项允许 pred 含解释前缀（取首个大写字母比对）
    if re.fullmatch(r"[A-Za-z]", gold):
        m = re.search(r"[A-Za-z]", pred)
        return bool(m) and m.group().upper() == gold.upper()
    if re.fullmatch(r"[A-Za-z]\d+", gold):  # S2 这类代号：允许带前缀词
        return bool(re.search(rf"(?<![A-Za-z0-9]){gold}(?![A-Za-z0-9])", pred, re.I))
    return pred.replace(" ", "").lower() == gold.replace(" ", "").lower()


def grade_item(item: dict, model_output: str):
    gold = str(item["target"]["answer"]).strip()
    tol = item["target"].get("tolerance")
    pred = extract_answer(model_output)
    gold_parts = [p for p in _SEP.split(gold) if p.strip()]
    pred_parts = [p for p in _SEP.split(pred) if p.strip()]
    if len(gold_parts) > 1:
        ok = len(pred_parts) == len(gold_parts) and all(
            _part_eq(p, g, tol) for p, g in zip(pred_parts, gold_parts)
        )
    else:
        ok = _part_eq(pred, gold, tol)
    return ok, pred


if __name__ == "__main__":
    # 自测
    cases = [
        ({"target": {"answer": "4.90", "tolerance": 0.02}}, "推理…\nANSWER: 4.91", True),
        ({"target": {"answer": "9", "tolerance": None}}, "ANSWER: 9 天", True),
        ({"target": {"answer": "9", "tolerance": None}}, "ANSWER: 6", False),
        ({"target": {"answer": "B,21", "tolerance": None}}, "ANSWER: B; 21", True),
        ({"target": {"answer": "6;2048", "tolerance": None}}, "ANSWER: 6, 2048 MB", True),
        ({"target": {"answer": "投;84.98", "tolerance": None}}, "ANSWER: 投；84.97", True),
        ({"target": {"answer": "S2", "tolerance": None}}, "ANSWER: 供应商 S2", False),
        ({"target": {"answer": "S2", "tolerance": None}}, "ANSWER: S2", True),
        ({"target": {"answer": "40/23", "tolerance": None}}, "ANSWER: 1.739", True),
        ({"target": {"answer": "50.4", "tolerance": 0.1}}, "ANSWER: 50.4%", True),
    ]
    for item, out, want in cases:
        got, pred = grade_item(item, out)
        flag = "OK " if got == want else "BAD"
        print(f"{flag} gold={item['target']['answer']!r} pred={pred!r} -> {got}")
