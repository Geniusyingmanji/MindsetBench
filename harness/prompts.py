"""Backward-compatible prompt entry point.

Usage: ``python3 harness/prompts.py <case_id> <condition> [library.md]``.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mindsetbench.models.case import Case  # noqa: E402
from mindsetbench.models.prompt import Condition, PromptContext  # noqa: E402
from mindsetbench.prompting import build_prompt  # noqa: E402

BANK = {
    row["id"]: Case.model_validate(row)
    for row in map(json.loads, open(ROOT / "data/all.jsonl", encoding="utf-8"))
}


def build(case_id: str, condition: str, library: str = "") -> str:
    context = PromptContext(skill_library=library or None)
    return build_prompt(BANK[case_id].prompt_view(), Condition(condition), context).user


def evolve_solve(case_id: str, library: str = "") -> str:
    item = BANK[case_id]
    skill = f"你此前积累的经验库（可参考）：\n{library.strip()}\n\n" if library.strip() else ""
    return (
        f"{skill}请解下面这道题。\n\n【题目】\n{item.target.problem}\n\n"
        "最后一行严格输出 ANSWER: <答案>。"
    )


def evolve_distill(case_id: str, my_answer: str, correct: bool) -> str:
    item = BANK[case_id]
    verdict = "正确" if correct else "错误"
    return (
        "你刚才解了下面这道题，系统只告诉你结果对错，不提供任何其他反馈。\n\n"
        f"【题目】\n{item.target.problem}\n\n"
        f"【你的答案】{my_answer}（判定：{verdict}）\n\n"
        "请蒸馏一条可复用、领域无关的解题洞察，格式严格为两行：\n"
        "[Insight] <一句话：抽象的解题策略/思维模式，不含本题具体数值与领域词汇>\n"
        "[When to use] <一句话：什么结构特征的问题适用>\n"
        "只输出这两行。若判定为错误，蒸馏如何避免这类失误的洞察。"
    )


if __name__ == "__main__":
    skill_library = open(sys.argv[3], encoding="utf-8").read() if len(sys.argv) > 3 else ""
    print(build(sys.argv[1], sys.argv[2], skill_library))
