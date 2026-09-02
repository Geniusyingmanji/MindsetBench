from decimal import Decimal

import pytest

from mindsetbench.grading import grade_response
from mindsetbench.models.answer import AnswerPart, AnswerSpec, AnswerType
from mindsetbench.models.case import CaseGoldView


def gold(
    value: str,
    answer_type: str | None = None,
    tolerance: float | None = None,
) -> CaseGoldView:
    return CaseGoldView(
        id="test",
        target_answer=AnswerSpec.from_legacy(value, answer_type, tolerance),
        copy_probe_answer=None,
        lure_answer=None,
    )


@pytest.mark.parametrize(
    ("expected", "output", "correct"),
    [
        (gold("4.90", tolerance=0.02), "推理\nANSWER: 4.91", True),
        (gold("9"), "ANSWER: 9", True),
        (gold("9"), "ANSWER: 9 天", False),
        (gold("B;21"), "ANSWER: B；21", True),
        (gold("S2", "string"), "ANSWER: 供应商 S2", False),
        (gold("S2", "string"), "ANSWER: S2", True),
        (gold("40/23"), "ANSWER: 1.739", True),
        (gold("50.4", tolerance=0.1), "ANSWER: 50.4%", True),
        (gold("9"), "答案是 9", False),
    ],
)
def test_grade_response(expected: CaseGoldView, output: str, correct: bool) -> None:
    assert grade_response(expected, output).correct is correct


def test_explicit_affix_policy() -> None:
    expected = CaseGoldView(
        id="test",
        target_answer=AnswerSpec(
            parts=[AnswerPart(type=AnswerType.LABEL, value="S2", allow_affixes=True)]
        ),
        copy_probe_answer=None,
        lure_answer=None,
    )
    assert grade_response(expected, "ANSWER: 供应商 S2").correct


def test_copy_probe_is_recorded() -> None:
    expected = CaseGoldView(
        id="test",
        target_answer=AnswerSpec.from_legacy("9"),
        copy_probe_answer=AnswerSpec.from_legacy("6"),
        lure_answer=None,
    )
    result = grade_response(expected, "ANSWER: 6")
    assert not result.correct
    assert result.matched_copy_probe


def test_per_part_tolerance() -> None:
    expected = CaseGoldView(
        id="test",
        target_answer=AnswerSpec(
            parts=[
                AnswerPart(type=AnswerType.NUMBER, value="1", abs_tolerance=Decimal("0")),
                AnswerPart(type=AnswerType.NUMBER, value="2", abs_tolerance=Decimal("0.1")),
            ]
        ),
        copy_probe_answer=None,
        lure_answer=None,
    )
    assert grade_response(expected, "ANSWER: 1;2.05").correct
    assert not grade_response(expected, "ANSWER: 1.01;2.05").correct
