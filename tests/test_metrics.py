from types import SimpleNamespace

from mindsetbench.metrics import (
    assess_calibration,
    copy_probe_rate_by_condition,
    paired_completed_condition_difference,
    paired_condition_difference,
    paired_outcome_counts,
    summarize_slices,
    summarize_transfer,
)
from mindsetbench.models.prompt import Condition


def _record(
    case_id: str,
    condition: Condition,
    correct: bool,
    *,
    level: int = 0,
    paradigm: str = "P1",
    finish_reason: str = "stop",
    output_tokens: int | None = 100,
    latency_ms: int = 1000,
    matched_copy_probe: bool = False,
    has_copy_probe: bool = False,
    sample_index: int = 0,
):
    return SimpleNamespace(
        case_id=case_id,
        condition=condition,
        sample_index=sample_index,
        level=level,
        paradigm=paradigm,
        has_copy_probe=has_copy_probe,
        response=SimpleNamespace(
            finish_reason=finish_reason,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        ),
        grade=SimpleNamespace(correct=correct, matched_copy_probe=matched_copy_probe),
    )


def test_condition_difference_uses_only_paired_cases() -> None:
    records = [
        _record("a", Condition.WITH_SOURCE, True),
        _record("a", Condition.WITH_LURE, False),
        _record("b", Condition.WITH_SOURCE, False),
    ]
    assert paired_condition_difference(records, Condition.WITH_SOURCE, Condition.WITH_LURE) == 1.0


def test_summarize_slices() -> None:
    records = [
        _record("a", Condition.TARGET_ONLY, False, level=2, paradigm="P2"),
        _record("a", Condition.WITH_SOURCE, True, level=2, paradigm="P2"),
        _record("a", Condition.WITH_LURE, False, level=2, paradigm="P2"),
    ]
    summary = summarize_slices(records)
    assert summary["by_level"]["2"]["transfer_gain"] == 1.0
    assert summary["by_paradigm"]["P2"]["structural_selectivity"] == 1.0


def test_transfer_summary_surfaces_truncated_trials() -> None:
    records = [
        _record("a", Condition.TARGET_ONLY, False, finish_reason="length"),
        _record("b", Condition.TARGET_ONLY, True),
    ]
    summary = summarize_transfer(records)
    assert summary["truncated_trials"] == 1
    assert summary["accuracy"]["target-only"] == 0.5
    assert summary["completed_accuracy"]["target-only"] == 1.0
    assert summary["completion_rate"]["target-only"] == 0.5


def test_completed_pairing_censors_either_truncated_side() -> None:
    records = [
        _record("a", Condition.TARGET_ONLY, False, finish_reason="length"),
        _record("a", Condition.WITH_SOURCE, False),
        _record("b", Condition.TARGET_ONLY, False),
        _record("b", Condition.WITH_SOURCE, True),
    ]
    assert paired_condition_difference(records, Condition.WITH_SOURCE, Condition.TARGET_ONLY) == 0.5
    assert (
        paired_completed_condition_difference(records, Condition.WITH_SOURCE, Condition.TARGET_ONLY)
        == 1.0
    )


def test_completed_efficiency_excludes_length_trials() -> None:
    records = [
        _record(
            "a",
            Condition.TARGET_ONLY,
            False,
            finish_reason="length",
            output_tokens=999,
            latency_ms=9000,
        ),
        _record(
            "b",
            Condition.TARGET_ONLY,
            True,
            output_tokens=120,
            latency_ms=1500,
        ),
    ]
    efficiency = summarize_transfer(records)["completed_efficiency"]["target-only"]
    assert efficiency == {
        "completed_trials": 1,
        "mean_output_tokens": 120,
        "median_output_tokens": 120,
        "mean_latency_ms": 1500,
        "median_latency_ms": 1500,
    }


def test_copy_probe_rate_is_reported_by_condition() -> None:
    records = [
        _record(
            "a",
            Condition.WITH_LURE,
            False,
            has_copy_probe=True,
            matched_copy_probe=True,
        ),
        _record("a", Condition.WITH_SOURCE, True, has_copy_probe=True),
    ]
    assert copy_probe_rate_by_condition(records) == {
        "with-lure": 1.0,
        "with-source": 0.0,
    }


def test_paired_outcome_counts_exposes_direction_of_disagreement() -> None:
    records = [
        _record("a", Condition.WITH_SOURCE, True),
        _record("a", Condition.TARGET_ONLY, False),
        _record("b", Condition.WITH_SOURCE, False),
        _record("b", Condition.TARGET_ONLY, True),
    ]
    assert paired_outcome_counts(
        records, Condition.WITH_SOURCE, Condition.TARGET_ONLY
    ) == {"paired_n": 2, "both": 0, "left_only": 1, "right_only": 1, "neither": 0}


def test_calibration_gate_requires_coverage_window_gain_and_selectivity() -> None:
    records = []
    for sample_index in range(3):
        records.extend(
            [
                _record(
                    "hard",
                    Condition.TARGET_ONLY,
                    sample_index == 0,
                    paradigm="P3",
                    sample_index=sample_index,
                ),
                _record(
                    "hard",
                    Condition.WITH_SOURCE,
                    True,
                    paradigm="P3",
                    sample_index=sample_index,
                ),
                _record(
                    "hard",
                    Condition.WITH_LURE,
                    False,
                    paradigm="P3",
                    sample_index=sample_index,
                ),
            ]
        )
    assessment = assess_calibration(records)["P3"]
    assert assessment["passed"]
    assert assessment["target_accuracy"] == 1 / 3


def test_calibration_gate_rejects_underfilled_ceiling_data() -> None:
    records = [
        _record("easy", Condition.TARGET_ONLY, True, paradigm="P4"),
        _record("easy", Condition.WITH_SOURCE, True, paradigm="P4"),
        _record("easy", Condition.WITH_LURE, True, paradigm="P4"),
    ]
    assessment = assess_calibration(records)["P4"]
    assert not assessment["passed"]
    assert "insufficient-coverage" in assessment["reasons"]
    assert "target-outside-window" in assessment["reasons"]
