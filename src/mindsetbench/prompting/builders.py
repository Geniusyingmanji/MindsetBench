from __future__ import annotations

import hashlib

from mindsetbench.models.case import CasePromptView
from mindsetbench.models.prompt import Condition, PromptArtifact, PromptContext

TEMPLATE_VERSION = "core-v3"
SYSTEM = "你是一个严谨的问题求解器。只依据用户提供的材料作答。"
TAIL = (
    "\n\n请给出必要的推理过程，并在最后一行严格输出：ANSWER: <答案>。"
    "多段答案使用分号分隔，不添加单位或解释。"
)


def condition_is_applicable(case: CasePromptView, condition: Condition) -> bool:
    if condition in {Condition.WITH_LURE, Condition.WITH_BOTH}:
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
    metadata: dict[str, str | int | None] = {"reference_case_id": context.reference_case_id}
    if condition == Condition.WITH_BOTH:
        metadata["reference_order"] = with_both_order(case.id)
    return PromptArtifact(
        case_id=case.id,
        condition=condition,
        system=SYSTEM,
        user=user,
        template_version=TEMPLATE_VERSION,
        prompt_sha256=digest,
        metadata=metadata,
    )


def with_both_order(case_id: str) -> str:
    """Deterministic, case-keyed presentation order for the unlabeled reference pair."""

    digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    return "source-first" if int(digest, 16) % 2 == 0 else "lure-first"


def _build_user(case: CasePromptView, condition: Condition, context: PromptContext) -> str:
    target = f"【目标题】\n{case.target_problem}"
    if case.answer_format:
        target += f"\n\n【答案格式】\n{case.answer_format}"
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
    if condition == Condition.WITH_BOTH:
        if case.lure is None:
            raise ValueError(f"case {case.id} has no lure")
        source_block = _reference_block(
            problem=case.source.problem,
            solution=case.source.solution,
            answer=case.source.answer,
        )
        lure_block = _reference_block(
            problem=case.lure.problem,
            solution=case.lure.solution or "（该参考题尚未提供结构化解答。）",
            answer=case.lure.answer.legacy_value() if case.lure.answer else "（未提供）",
        )
        ordered = (
            (source_block, lure_block)
            if with_both_order(case.id) == "source-first"
            else (lure_block, source_block)
        )
        return (
            "先阅读两道已解出的参考题。它们与目标题的相关性未知，可能有一道、两道或没有一道"
            "与目标题共享解题结构；请自行判断后再解决目标题。\n\n"
            f"【参考题一】\n{ordered[0]}\n\n【参考题二】\n{ordered[1]}\n\n{target}{TAIL}"
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


def _reference_block(*, problem: str, solution: str, answer: str) -> str:
    return f"{problem}\n\n解答：{solution}\n答案：{answer}"
