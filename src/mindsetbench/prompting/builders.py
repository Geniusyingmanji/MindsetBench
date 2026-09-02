from __future__ import annotations

import hashlib

from mindsetbench.models.case import CasePromptView
from mindsetbench.models.prompt import Condition, PromptArtifact, PromptContext

TEMPLATE_VERSION = "core-v2"
SYSTEM = "你是一个严谨的问题求解器。只依据用户提供的材料作答。"
TAIL = (
    "\n\n请给出必要的推理过程，并在最后一行严格输出：ANSWER: <答案>。"
    "多段答案使用分号分隔，不添加单位或解释。"
)


def condition_is_applicable(case: CasePromptView, condition: Condition) -> bool:
    if condition == Condition.WITH_LURE:
        return case.lure is not None
    if condition == Condition.H3_FALSE_MINDSET:
        return case.hints.false_mindset is not None
    if condition == Condition.HOP_TRANSFER:
        return case.hop is not None
    return True


def build_prompt(
    case: CasePromptView,
    condition: Condition,
    context: PromptContext | None = None,
) -> PromptArtifact:
    context = context or PromptContext()
    user = _build_user(case, condition, context)
    digest = hashlib.sha256(f"{SYSTEM}\n{user}\n{TEMPLATE_VERSION}".encode()).hexdigest()
    return PromptArtifact(
        case_id=case.id,
        condition=condition,
        system=SYSTEM,
        user=user,
        template_version=TEMPLATE_VERSION,
        prompt_sha256=digest,
        metadata={"reference_case_id": context.reference_case_id},
    )


def _build_user(case: CasePromptView, condition: Condition, context: PromptContext) -> str:
    target = f"【目标题】\n{case.target_problem}"
    if condition == Condition.TARGET_ONLY:
        return f"请解下面这道题。\n\n{target}{TAIL}"
    if condition == Condition.RANDOM_SOURCE:
        if not context.reference_problem:
            raise ValueError("random-source requires a matched reference problem")
        solution = (
            f"\n\n【参考题解答】\n{context.reference_solution}"
            if context.reference_solution
            else ""
        )
        return (
            "先阅读一道长度和难度相近、但不保证相关的参考题，再独立解决目标题。\n\n"
            f"【参考题】\n{context.reference_problem}{solution}\n\n{target}{TAIL}"
        )
    if condition in {Condition.WITH_SOURCE, Condition.H4_SOURCE_SOLUTION}:
        return _solved_reference_prompt(
            problem=case.source.problem,
            solution=case.source.solution,
            answer=case.source.answer,
            target=target,
        )
    if condition == Condition.WITH_LURE:
        if case.lure is None:
            raise ValueError(f"case {case.id} has no lure")
        solution = case.lure.solution or "（该旧版题目尚未提供结构化解答，请自行判断其相关性。）"
        answer = case.lure.answer.legacy_value() if case.lure.answer else "（未提供）"
        return _solved_reference_prompt(
            problem=case.lure.problem,
            solution=solution,
            answer=answer,
            target=target,
        )
    if condition == Condition.H1_SOURCE_PROBLEM:
        return (
            "下面另一领域的题可能与目标题相关。先阅读题面，但不给参考解答。\n\n"
            f"【参考题】\n{case.source.problem}\n\n{target}{TAIL}"
        )
    if condition == Condition.H2_SCHEMA_NAME:
        return f"提示：本题涉及“{case.schema_name}”。\n\n{target}{TAIL}"
    if condition == Condition.H3_ORACLE_MINDSET:
        mindset = case.hints.oracle_mindset
        insight = mindset.insight if mindset else "；".join(case.shared_relations)
        when = mindset.when_to_use if mindset else "当不同领域的问题共享这些关系结构时。"
        return f"[Insight] {insight}\n[When to use] {when}\n\n{target}{TAIL}"
    if condition == Condition.H3_FALSE_MINDSET:
        mindset = case.hints.false_mindset
        if mindset is None:
            raise ValueError(f"case {case.id} has no false mindset")
        return f"[Insight] {mindset.insight}\n[When to use] {mindset.when_to_use}\n\n{target}{TAIL}"
    if condition == Condition.H5_MAPPING:
        mapping = "\n".join(
            f"- {source} ↔ {target_name}" for source, target_name in case.mapping_objects.items()
        )
        return (
            f"【参考题】\n{case.source.problem}\n\n【参考题解答】\n{case.source.solution}\n\n"
            f"【对象映射】\n{mapping}\n\n{target}{TAIL}"
        )
    if condition == Condition.WITH_SKILL:
        if not context.skill_library:
            raise ValueError("with-skill requires a non-empty skill library")
        return f"【经验库】\n{context.skill_library.strip()}\n\n{target}{TAIL}"
    if condition in {Condition.HOP_TRANSFER, Condition.PREFIX_TRANSFER}:
        if not context.prefix_material:
            raise ValueError(f"{condition.value} requires prefix material")
        prefix = "\n\n".join(context.prefix_material)
        return f"【此前已解任务】\n{prefix}\n\n{target}{TAIL}"
    raise ValueError(f"unsupported condition: {condition}")


def _solved_reference_prompt(*, problem: str, solution: str, answer: str, target: str) -> str:
    """Keep source and lure conditions blinded: only their content may differ."""

    return (
        "先阅读一道已解出的参考题，再解决目标题。\n\n"
        f"【参考题】\n{problem}\n\n"
        f"【参考题解答】\n{solution}\n"
        f"【参考题答案】\n{answer}\n\n{target}{TAIL}"
    )
