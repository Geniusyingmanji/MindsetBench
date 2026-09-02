from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from statistics import mean, median

from mindsetbench.models.prompt import Condition
from mindsetbench.models.run import TrialRecord


def accuracy_by_condition(records: Sequence[TrialRecord]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        grouped[record.condition.value].append(record.grade.correct)
    return {
        condition: sum(outcomes) / len(outcomes)
        for condition, outcomes in sorted(grouped.items())
        if outcomes
    }


def summarize_transfer(records: Sequence[TrialRecord]) -> dict[str, object]:
    accuracies = accuracy_by_condition(records)
    copy_probe_records = [record for record in records if record.has_copy_probe]
    completed = [record for record in records if record.response.finish_reason != "length"]
    return {
        "trials": len(records),
        "truncated_trials": len(records) - len(completed),
        "accuracy": accuracies,
        "completed_accuracy": accuracy_by_condition(completed),
        "part_accuracy": part_accuracy_by_condition(records),
        "completed_part_accuracy": part_accuracy_by_condition(completed),
        "completion_rate": _completion_rate_by_condition(records),
        "transfer_gain": paired_condition_difference(
            records, Condition.WITH_SOURCE, Condition.TARGET_ONLY
        ),
        "completed_transfer_gain": paired_completed_condition_difference(
            records, Condition.WITH_SOURCE, Condition.TARGET_ONLY
        ),
        "context_adjusted_gain": paired_condition_difference(
            records, Condition.WITH_SOURCE, Condition.RANDOM_SOURCE
        ),
        "structural_selectivity": paired_condition_difference(
            records, Condition.WITH_SOURCE, Condition.WITH_LURE
        ),
        "completed_structural_selectivity": paired_completed_condition_difference(
            records, Condition.WITH_SOURCE, Condition.WITH_LURE
        ),
        "completed_efficiency": completed_efficiency_by_condition(records),
        "copy_probe_rate": (
            sum(record.grade.matched_copy_probe for record in copy_probe_records)
            / len(copy_probe_records)
            if copy_probe_records
            else None
        ),
        "copy_probe_rate_by_condition": copy_probe_rate_by_condition(records),
        "source_vs_target_pairs": paired_outcome_counts(
            records, Condition.WITH_SOURCE, Condition.TARGET_ONLY
        ),
        "source_vs_lure_pairs": paired_outcome_counts(
            records, Condition.WITH_SOURCE, Condition.WITH_LURE
        ),
    }


def part_accuracy_by_condition(
    records: Sequence[TrialRecord],
) -> dict[str, dict[str, float | int | None]]:
    """Micro-average answer-part accuracy while exposing parse coverage.

    Old result rows may predate explicit part counts. Such rows are scored when
    their saved ``part_results`` reveal a count and otherwise reported as
    unscored rather than silently treated as single-part answers.
    """

    grouped: dict[str, list[TrialRecord]] = defaultdict(list)
    for record in records:
        grouped[record.condition.value].append(record)
    summaries: dict[str, dict[str, float | int | None]] = {}
    for condition, condition_records in sorted(grouped.items()):
        expected_parts = 0
        observed_parts = 0
        correct_parts = 0
        scored_trials = 0
        for record in condition_records:
            part_results = record.grade.part_results
            expected = getattr(record.grade, "expected_part_count", None)
            if expected is None and part_results:
                expected = max(part.index for part in part_results) + 1
            if expected is None:
                continue
            scored_trials += 1
            expected_parts += expected
            by_index = {part.index: part for part in part_results}
            for index in range(expected):
                result = by_index.get(index)
                if result is not None and result.predicted is not None:
                    observed_parts += 1
                if result is not None and result.correct:
                    correct_parts += 1
        summaries[condition] = {
            "trials": len(condition_records),
            "scored_trials": scored_trials,
            "unscored_trials": len(condition_records) - scored_trials,
            "correct_parts": correct_parts,
            "observed_parts": observed_parts,
            "expected_parts": expected_parts,
            "accuracy": correct_parts / expected_parts if expected_parts else None,
            "coverage": observed_parts / expected_parts if expected_parts else None,
        }
    return summaries


def part_scores_by_case_condition(
    records: Sequence[TrialRecord],
) -> dict[str, dict[str, dict[str, dict[str, float | int | None]]]]:
    """Detailed part metrics for diagnostic reports, grouped without mixing cases."""

    grouped: dict[tuple[str, str], list[TrialRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.case_id, record.condition.value)].append(record)
    output: dict[str, dict[str, dict[str, dict[str, float | int | None]]]] = {}
    for (case_id, condition), condition_records in sorted(grouped.items()):
        expected_counts = [
            count
            for record in condition_records
            if (count := getattr(record.grade, "expected_part_count", None)) is not None
        ]
        if expected_counts:
            expected_count = max(expected_counts)
        else:
            indexes = [
                part.index for record in condition_records for part in record.grade.part_results
            ]
            expected_count = max(indexes, default=-1) + 1
        part_output: dict[str, dict[str, float | int | None]] = {}
        for index in range(expected_count):
            results = [
                next((part for part in record.grade.part_results if part.index == index), None)
                for record in condition_records
            ]
            observed = sum(
                result is not None and result.predicted is not None for result in results
            )
            correct = sum(result is not None and result.correct for result in results)
            total = len(condition_records)
            part_output[str(index)] = {
                "trials": total,
                "observed": observed,
                "correct": correct,
                "accuracy": correct / total if total else None,
                "coverage": observed / total if total else None,
            }
        output.setdefault(case_id, {})[condition] = part_output
    return output


def copy_probe_rate_by_condition(records: Sequence[TrialRecord]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        if record.has_copy_probe:
            grouped[record.condition.value].append(record.grade.matched_copy_probe)
    return {
        condition: sum(matches) / len(matches)
        for condition, matches in sorted(grouped.items())
        if matches
    }


def paired_outcome_counts(
    records: Sequence[TrialRecord],
    left: Condition,
    right: Condition,
) -> dict[str, int]:
    indexed: dict[Condition, dict[tuple[str, int], bool]] = defaultdict(dict)
    for record in records:
        indexed[record.condition][(record.case_id, record.sample_index)] = record.grade.correct
    common = set(indexed[left]) & set(indexed[right])
    counts = {"paired_n": len(common), "both": 0, "left_only": 0, "right_only": 0, "neither": 0}
    for key in common:
        left_correct = indexed[left][key]
        right_correct = indexed[right][key]
        if left_correct and right_correct:
            counts["both"] += 1
        elif left_correct:
            counts["left_only"] += 1
        elif right_correct:
            counts["right_only"] += 1
        else:
            counts["neither"] += 1
    return counts


def assess_calibration(
    records: Sequence[TrialRecord],
    *,
    min_samples_per_case_condition: int = 3,
    target_window: tuple[float, float] = (0.2, 0.6),
    min_source_gain: float = 0.15,
) -> dict[str, dict[str, object]]:
    """Apply preregistered calibration gates independently to each paradigm."""

    grouped: dict[str, list[TrialRecord]] = defaultdict(list)
    for record in records:
        grouped[record.paradigm].append(record)
    return {
        paradigm: _assess_group(
            group_records,
            min_samples_per_case_condition=min_samples_per_case_condition,
            target_window=target_window,
            min_source_gain=min_source_gain,
        )
        for paradigm, group_records in sorted(grouped.items())
    }


def _assess_group(
    records: Sequence[TrialRecord],
    *,
    min_samples_per_case_condition: int,
    target_window: tuple[float, float],
    min_source_gain: float,
) -> dict[str, object]:
    required_conditions = {
        Condition.TARGET_ONLY,
        Condition.WITH_SOURCE,
        Condition.WITH_LURE,
    }
    cases = sorted({record.case_id for record in records})
    coverage: dict[tuple[str, Condition], int] = defaultdict(int)
    for record in records:
        coverage[(record.case_id, record.condition)] += 1
    missing = [
        f"{case_id}|{condition.value}"
        for case_id in cases
        for condition in sorted(required_conditions, key=lambda item: item.value)
        if coverage[(case_id, condition)] < min_samples_per_case_condition
    ]
    target_accuracy = accuracy_by_condition(records).get(Condition.TARGET_ONLY.value)
    source_gain = paired_condition_difference(records, Condition.WITH_SOURCE, Condition.TARGET_ONLY)
    selectivity = paired_condition_difference(records, Condition.WITH_SOURCE, Condition.WITH_LURE)
    completion = _completion_rate_by_condition(records)
    reasons: list[str] = []
    if missing:
        reasons.append("insufficient-coverage")
    if target_accuracy is None or not target_window[0] <= target_accuracy <= target_window[1]:
        reasons.append("target-outside-window")
    if source_gain is None or source_gain < min_source_gain:
        reasons.append("source-gain-below-threshold")
    if selectivity is None or selectivity <= 0:
        reasons.append("nonpositive-structural-selectivity")
    if any(completion.get(condition.value, 0.0) < 0.8 for condition in required_conditions):
        reasons.append("completion-rate-below-0.8")
    return {
        "passed": not reasons,
        "cases": cases,
        "missing_or_underfilled": missing,
        "target_accuracy": target_accuracy,
        "source_gain": source_gain,
        "structural_selectivity": selectivity,
        "completion_rate": completion,
        "reasons": reasons,
    }


def _completion_rate_by_condition(records: Sequence[TrialRecord]) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        grouped[record.condition.value].append(record.response.finish_reason != "length")
    return {
        condition: sum(outcomes) / len(outcomes)
        for condition, outcomes in sorted(grouped.items())
        if outcomes
    }


def completed_efficiency_by_condition(
    records: Sequence[TrialRecord],
) -> dict[str, dict[str, float | int | None]]:
    """Token and latency summaries over completed, non-censored trials only."""

    grouped: dict[str, list[TrialRecord]] = defaultdict(list)
    for record in records:
        if record.response.finish_reason != "length":
            grouped[record.condition.value].append(record)

    summaries: dict[str, dict[str, float | int | None]] = {}
    for condition, condition_records in sorted(grouped.items()):
        output_tokens = [
            record.response.output_tokens
            for record in condition_records
            if record.response.output_tokens is not None
        ]
        latencies = [record.response.latency_ms for record in condition_records]
        summaries[condition] = {
            "completed_trials": len(condition_records),
            "mean_output_tokens": mean(output_tokens) if output_tokens else None,
            "median_output_tokens": median(output_tokens) if output_tokens else None,
            "mean_latency_ms": mean(latencies) if latencies else None,
            "median_latency_ms": median(latencies) if latencies else None,
        }
    return summaries


def summarize_slices(records: Sequence[TrialRecord]) -> dict[str, object]:
    """Condition outcomes sliced by level, paradigm, and source/schema design."""

    return {
        "by_level": _group_summaries(records, lambda record: str(record.level)),
        "by_paradigm": _group_summaries(records, lambda record: record.paradigm),
        "by_schema": _group_summaries(records, lambda record: record.schema_id),
    }


def _group_summaries(
    records: Sequence[TrialRecord],
    key: Callable[[TrialRecord], str],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[TrialRecord]] = defaultdict(list)
    for record in records:
        grouped[key(record)].append(record)
    return {
        group: {
            "n": len(group_records),
            "accuracy": accuracy_by_condition(group_records),
            "part_accuracy": part_accuracy_by_condition(group_records),
            "completion_rate": _completion_rate_by_condition(group_records),
            "copy_probe_rate": copy_probe_rate_by_condition(group_records),
            "transfer_gain": paired_condition_difference(
                group_records, Condition.WITH_SOURCE, Condition.TARGET_ONLY
            ),
            "structural_selectivity": paired_condition_difference(
                group_records, Condition.WITH_SOURCE, Condition.WITH_LURE
            ),
        }
        for group, group_records in sorted(grouped.items())
    }


def paired_condition_difference(
    records: Sequence[TrialRecord],
    left: Condition,
    right: Condition,
) -> float | None:
    indexed: dict[Condition, dict[tuple[str, int], bool]] = defaultdict(dict)
    for record in records:
        indexed[record.condition][(record.case_id, record.sample_index)] = record.grade.correct
    common = set(indexed[left]) & set(indexed[right])
    if not common:
        return None
    differences = [int(indexed[left][key]) - int(indexed[right][key]) for key in common]
    return sum(differences) / len(differences)


def paired_completed_condition_difference(
    records: Sequence[TrialRecord],
    left: Condition,
    right: Condition,
) -> float | None:
    """Paired condition difference after censoring length-truncated trials."""

    completed = [record for record in records if record.response.finish_reason != "length"]
    return paired_condition_difference(completed, left, right)
