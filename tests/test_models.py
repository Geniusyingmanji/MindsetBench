from mindsetbench.data import load_cases
from mindsetbench.models.case import CasePromptView


def test_loads_all_legacy_cases() -> None:
    cases = load_cases()
    assert len(cases) == 85
    assert len({case.id for case in cases}) == 85
    assert {case.level for case in cases} == {0, 1, 2, 3, 4}


def test_prompt_view_has_no_target_gold_field() -> None:
    fields = set(CasePromptView.model_fields)
    assert "target_answer" not in fields
    assert "target_problem" in fields


def test_legacy_answer_is_normalized_to_parts() -> None:
    case = next(case for case in load_cases() if case.id == "L4-A-C1")
    assert [part.value for part in case.target.answer.parts] == ["6", "2048"]
