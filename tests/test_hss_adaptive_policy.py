from collections import Counter

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    validate_dataset,
    validate_transfer_design,
)
from mindsetbench.models.prompt import Condition
from mindsetbench.prompting import build_prompt
from mindsetbench.verification import verify_case

DATASET = PROJECT_ROOT / "data" / "v1" / "hss-adaptive-policy-seeds.yaml"
MANIFEST = PROJECT_ROOT / "data" / "manifests" / "hss-adaptive-policy4.json"


def test_adaptive_policy_seeds_are_strict_audited_and_executable() -> None:
    cases = load_cases(DATASET)
    strict = validate_dataset(cases, strict_v1=True)
    audit = validate_transfer_design(cases)
    assert strict.ok, strict.issues
    assert audit.ok, audit.issues
    assert len(cases) == 4
    assert Counter(case.paradigm.value for case in cases) == {
        "P4": 1,
        "P6": 1,
        "P7": 1,
        "P8": 1,
    }
    assert all(case.level == 4 for case in cases)

    results = [verify_case(case) for case in cases]
    assert all(result.passed for result in results), results


def test_adaptive_policy_manifest_matches_direct_dataset() -> None:
    assert [case.id for case in load_cases(MANIFEST)] == [case.id for case in load_cases(DATASET)]


def test_adaptive_policy_answer_contracts_are_nonleaking() -> None:
    for case in load_cases(DATASET):
        assert case.source.domain != case.target.domain
        assert "最多两次" in case.target.problem
        assert "第二次" in case.target.problem
        assert case.target.answer_format
        assert case.target.answer.legacy_value() not in case.target.answer_format
        assert case.target.answer.parts[0].value.startswith("ROOT=Q")
        assert case.lure is not None and case.lure.answer is not None
        assert case.copy_probe is not None
        assert case.copy_probe.answer == case.lure.answer
        assert case.copy_probe.answer != case.target.answer

        prompt = build_prompt(case.prompt_view(), Condition.TARGET_ONLY)
        assert f"【答案格式】\n{case.target.answer_format}" in prompt.user


def test_adaptive_policy_gold_and_lure_change_the_first_query() -> None:
    for case in load_cases(DATASET):
        assert case.lure is not None and case.lure.answer is not None
        assert case.target.answer.parts[0] != case.lure.answer.parts[0]
