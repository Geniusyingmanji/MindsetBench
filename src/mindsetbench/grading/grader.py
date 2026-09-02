from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from mindsetbench.models.answer import AnswerPart, AnswerSpec, AnswerType
from mindsetbench.models.case import CaseGoldView
from mindsetbench.models.run import GradeResult, PartGrade

_ANSWER_RE = re.compile(r"^\s*ANSWER\s*[:：]\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)


def extract_answer(text: str, *, require_marker: bool = True) -> tuple[str | None, str | None]:
    matches = _ANSWER_RE.findall(text)
    if matches:
        answer = matches[-1].strip()
        return (answer or None), (None if answer else "empty-answer")
    if require_marker:
        return None, "missing-answer-marker"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (lines[-1], None) if lines else (None, "empty-response")


def grade_response(
    gold: CaseGoldView,
    model_output: str,
    *,
    require_marker: bool = True,
) -> GradeResult:
    expected_part_count = len(gold.target_answer.parts)
    extracted, parse_error = extract_answer(model_output, require_marker=require_marker)
    if extracted is None:
        return GradeResult(
            correct=False,
            extracted=None,
            expected_part_count=expected_part_count,
            parsed_part_count=0,
            parse_error=parse_error,
        )

    correct, part_results, normalized = _match_answer(extracted, gold.target_answer)
    copy_match = bool(
        gold.copy_probe_answer and _match_answer(extracted, gold.copy_probe_answer)[0]
    )
    lure_match = bool(gold.lure_answer and _match_answer(extracted, gold.lure_answer)[0])
    return GradeResult(
        correct=correct,
        extracted=extracted,
        normalized_parts=normalized,
        part_results=part_results,
        expected_part_count=expected_part_count,
        parsed_part_count=len(normalized),
        parse_error=parse_error,
        matched_copy_probe=copy_match,
        matched_lure_answer=lure_match,
    )


def _match_answer(raw: str, spec: AnswerSpec) -> tuple[bool, list[PartGrade], list[str]]:
    chunks = [part.strip() for part in _split_parts(raw, spec.separator) if part.strip()]
    expected = spec.parts
    results: list[PartGrade] = []
    for index, answer_part in enumerate(expected):
        if index >= len(chunks):
            results.append(
                PartGrade(
                    index=index,
                    correct=False,
                    predicted=None,
                    expected=answer_part.value,
                    reason="missing-part",
                )
            )
            continue
        predicted = chunks[index]
        ok, reason = _match_part(predicted, answer_part)
        results.append(
            PartGrade(
                index=index,
                correct=ok,
                predicted=predicted,
                expected=answer_part.value,
                reason=reason,
            )
        )
    count_matches = len(chunks) == len(expected)
    if len(chunks) > len(expected) and results:
        results[-1].reason = f"extra-parts:{len(chunks) - len(expected)}"
    return count_matches and all(result.correct for result in results), results, chunks


def _split_parts(raw: str, separator: str) -> list[str]:
    if separator == ";":
        pattern = r"[;；]"
    elif separator == ",":
        pattern = r"[,，]"
    else:
        pattern = re.escape(separator)
    return re.split(pattern, raw)


def _match_part(predicted: str, expected: AnswerPart) -> tuple[bool, str | None]:
    if expected.type in {AnswerType.NUMBER, AnswerType.FRACTION, AnswerType.PERCENTAGE}:
        pred_number = _parse_number(predicted)
        gold_number = _parse_number(expected.value)
        if pred_number is None or gold_number is None:
            return False, "not-numeric"
        difference = abs(pred_number - gold_number)
        absolute = expected.abs_tolerance
        relative = expected.rel_tolerance
        if absolute is None and relative is None:
            if gold_number == gold_number.to_integral_value():
                absolute = Decimal("0")
            else:
                absolute = Decimal("0.005")
                relative = Decimal("0.005")
        threshold = max(
            absolute or Decimal("0"),
            abs(gold_number) * (relative or Decimal("0")),
        )
        return difference <= threshold, None if difference <= threshold else "out-of-tolerance"

    pred_text = _normalize_text(predicted, case_sensitive=expected.case_sensitive)
    gold_text = _normalize_text(expected.value, case_sensitive=expected.case_sensitive)
    if expected.allow_affixes:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(gold_text)}(?![A-Za-z0-9])"
        ok = bool(re.search(pattern, pred_text))
    else:
        ok = pred_text == gold_text
    return ok, None if ok else "text-mismatch"


def _parse_number(value: str) -> Decimal | None:
    cleaned = value.strip().rstrip("。. ").replace("％", "%")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1].strip()
    try:
        if "/" in cleaned:
            fraction = Fraction(cleaned)
            return Decimal(fraction.numerator) / Decimal(fraction.denominator)
        return Decimal(cleaned)
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return None


def _normalize_text(value: str, *, case_sensitive: bool) -> str:
    normalized = "".join(value.strip().rstrip("。. ").split())
    return normalized if case_sensitive else normalized.casefold()
