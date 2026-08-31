"""三条件提示构造器。python3 prompts.py <case_id> <condition> [library.md] 输出完整 prompt。"""
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = {r["id"]: r for r in map(json.loads, open(ROOT / "data/all.jsonl"))}

TAIL = "\n\n要求：给出推理过程后，最后一行严格按格式输出：ANSWER: <答案>。多段式答案用分号分隔，只写答案本身，不加单位与解释。"


def build(case_id: str, condition: str, library: str = "") -> str:
    it = BANK[case_id]
    tgt = it["target"]["problem"]
    if condition == "target-only":
        return f"请解下面这道题。\n\n【题目】\n{tgt}{TAIL}"
    if condition == "with-skill":
        return (
            "你在长期任务流中积累了下面的经验库，其中的洞察可能与本题相关，也可能无关，请自行判断。\n\n"
            f"【经验库】\n{library.strip()}\n\n【题目】\n{tgt}{TAIL}"
        )
    if condition == "with-source":
        src = it["source"]
        return (
            "先阅读一道已解出的参考题（可能对你有启发），再解目标题。\n\n"
            f"【参考题｜{src['domain']}】\n{src['problem']}\n\n"
            f"【参考题解答】\n{src['solution']}\n（参考题答案：{src['answer']}）\n\n"
            f"【目标题】\n{tgt}{TAIL}"
        )
    raise ValueError(condition)


def evolve_solve(case_id: str, library: str = "") -> str:
    it = BANK[case_id]
    lib = f"你此前积累的经验库（可参考）：\n{library.strip()}\n\n" if library.strip() else ""
    return f"{lib}请解下面这道题。\n\n【题目】\n{it['target']['problem']}{TAIL}"


def evolve_distill(case_id: str, my_answer: str, correct: bool) -> str:
    it = BANK[case_id]
    verdict = "正确" if correct else "错误"
    return (
        "你刚才解了下面这道题，系统只告诉你结果对错，不提供任何其他反馈。\n\n"
        f"【题目】\n{it['target']['problem']}\n\n"
        f"【你的答案】{my_answer}（判定：{verdict}）\n\n"
        "请蒸馏一条可复用、领域无关的解题洞察，格式严格为两行：\n"
        "[Insight] <一句话：抽象的解题策略/思维模式，不含本题具体数值与领域词汇>\n"
        "[When to use] <一句话：什么结构特征的问题适用>\n"
        "只输出这两行。若判定为错误，蒸馏'如何避免这类失误'的洞察。"
    )


if __name__ == "__main__":
    lib = open(sys.argv[3]).read() if len(sys.argv) > 3 else ""
    print(build(sys.argv[1], sys.argv[2], lib))
