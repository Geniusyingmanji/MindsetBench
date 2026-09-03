import pytest

from mindsetbench.data import PROJECT_ROOT, load_cases
from mindsetbench.models.prompt import Condition, PromptContext
from mindsetbench.prompting import build_prompt


@pytest.fixture(scope="module")
def cases_by_id():
    return {case.id: case for case in load_cases()}


def test_with_lure_is_implemented(cases_by_id) -> None:
    case = cases_by_id["L2-F-05"]
    prompt = build_prompt(case.prompt_view(), Condition.WITH_LURE)
    assert "零级动力学" in prompt.user
    assert case.target.problem in prompt.user
    assert "表面上可能相关" not in prompt.user


def test_source_and_lure_conditions_use_blinded_template(cases_by_id) -> None:
    case = cases_by_id["L2-F-05"]
    source = build_prompt(case.prompt_view(), Condition.WITH_SOURCE)
    lure = build_prompt(case.prompt_view(), Condition.WITH_LURE)
    assert source.user.split("【参考题】", 1)[0] == lure.user.split("【参考题】", 1)[0]


def test_prompt_hash_is_deterministic(cases_by_id) -> None:
    view = cases_by_id["L3-A-01"].prompt_view()
    first = build_prompt(view, Condition.WITH_SOURCE)
    second = build_prompt(view, Condition.WITH_SOURCE)
    assert first.prompt_sha256 == second.prompt_sha256


def test_structured_answer_format_is_injected_without_gold() -> None:
    case = next(
        case
        for case in load_cases(
            PROJECT_ROOT / "data" / "v1" / "hss-p7-argument-evidence-chain.yaml"
        )
        if case.id == "HSS-P7-ARG-EVIDENCE-L3-01"
    )
    prompt = build_prompt(case.prompt_view(), Condition.TARGET_ONLY)
    assert "【答案格式】" in prompt.user
    assert case.target.answer_format in prompt.user
    assert case.target.answer.legacy_value() not in case.target.answer_format


def test_random_source_requires_explicit_context(cases_by_id) -> None:
    with pytest.raises(ValueError, match="random-source"):
        build_prompt(cases_by_id["L3-A-01"].prompt_view(), Condition.RANDOM_SOURCE)


def test_random_source_records_reference(cases_by_id) -> None:
    case = cases_by_id["L3-A-01"]
    context = PromptContext(
        reference_case_id="other",
        reference_problem="Unrelated problem",
        reference_solution="Unrelated solution",
    )
    prompt = build_prompt(case.prompt_view(), Condition.RANDOM_SOURCE, context)
    assert prompt.metadata["reference_case_id"] == "other"


def test_false_mindset_requires_material(cases_by_id) -> None:
    with pytest.raises(ValueError, match="false mindset"):
        build_prompt(cases_by_id["L3-A-01"].prompt_view(), Condition.H3_FALSE_MINDSET)
