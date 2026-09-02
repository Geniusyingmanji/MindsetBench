from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    validate_dataset,
    validate_transfer_design,
)
from mindsetbench.models.prompt import Condition
from mindsetbench.prompting import build_prompt
from mindsetbench.verification import verify_case
from mindsetbench.verification.formal_p5_latent import (
    CATALOGUE,
    CHAIN_LEVEL_SPECS,
    L4_CATALOGUE,
    Q2_CERTIFICATE_SPECS,
    Q2_CONJUGATE_VARIANTS,
    _format_certificate,
    _optimality_certificate,
    _parse_problem,
)

DATASET = PROJECT_ROOT / "data" / "v1" / "p5-latent-seeds.yaml"
CHAIN_DATASET = PROJECT_ROOT / "data" / "v1" / "formal-p5-latent-chain.yaml"
STAGED_DATASET = PROJECT_ROOT / "data" / "v1" / "p5-latent-staged.yaml"
CERTIFICATE_DATASET = PROJECT_ROOT / "data" / "manifests" / "p5-latent-certificates.json"
DECOUPLED_CERTIFICATE_DATASET = (
    PROJECT_ROOT / "data" / "manifests" / "p5-latent-certificates-decoupled.json"
)


def test_p5_latent_seed_is_strict_and_verified() -> None:
    cases = load_cases(DATASET)
    report = validate_dataset(cases, strict_v1=True)
    assert report.ok, report.issues
    assert len(cases) == 1
    result = verify_case(cases[0])
    assert result.passed, result
    assert len(result.checks) == 19


def test_p5_latent_seed_has_deterministic_negative_control() -> None:
    case = load_cases(DATASET)[0]
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    assert case.copy_probe.answer == case.lure.answer
    assert case.copy_probe.answer != case.target.answer


def test_p5_latent_verifier_rejects_calibration_log_drift() -> None:
    case = load_cases(DATASET)[0].model_copy(deep=True)
    assert "K7:10010111→01011110" in case.target.problem
    case.target.problem = case.target.problem.replace(
        "K7:10010111→01011110",
        "K7:10010111→01011111",
        1,
    )
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-text-problem" for check in result.checks)


def test_p5_latent_chain_is_complete_strict_and_verified() -> None:
    cases = load_cases(CHAIN_DATASET)
    report = validate_transfer_design(cases, require_complete_chains=True)
    assert report.ok, report.issues
    assert [case.level for case in cases] == [0, 1, 2, 3, 4]
    assert len({case.chain for case in cases}) == 1
    for case in cases:
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == 16


def test_p5_latent_l4_set_representation_matches_bit_affine_catalogue() -> None:
    bit_transforms = dict(CATALOGUE)
    set_transforms = dict(L4_CATALOGUE)
    for index in range(1, 10):
        bit_transform = bit_transforms[f"F{index}"]
        set_transform = set_transforms[f"G{index}"]
        assert all(bit_transform.apply(state) == set_transform.apply(state) for state in range(256))

    l4_case = load_cases(CHAIN_DATASET)[4]
    assert _parse_problem(l4_case.target.problem) == CHAIN_LEVEL_SPECS[4].target


def test_p5_latent_l4_verifier_rejects_set_toggle_drift() -> None:
    case = load_cases(CHAIN_DATASET)[4].model_copy(deep=True)
    assert "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}" in case.target.problem
    case.target.problem = case.target.problem.replace(
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}",
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,g}",
        1,
    )
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-text-problem" for check in result.checks)


def test_formal30_manifest_has_no_duplicate_cases() -> None:
    cases = load_cases(PROJECT_ROOT / "data" / "manifests" / "formal30.json")
    assert len(cases) == 30
    assert len({case.id for case in cases}) == 30


def test_p5_latent_staged_probes_are_strict_audited_and_verified() -> None:
    cases = load_cases(STAGED_DATASET)
    report = validate_transfer_design(cases)
    assert report.ok, report.issues
    assert [case.id for case in cases] == [
        "DIAG-P5-LATENT-L4-ID-01",
        "DIAG-P5-LATENT-L4-PLAN-01",
        "DIAG-P5-LATENT-L4-PLAN-Q1-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-01",
        "DIAG-P5-LATENT-L4-PLAN-Q3-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-V1-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-V2-01",
    ]
    expected_checks = [13, 15, 15, 15, 15, 17, 17]
    for case, check_count in zip(cases, expected_checks, strict=True):
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == check_count


def test_staged_identification_and_planning_match_full_l4_gold() -> None:
    identification, planning, *single_queries = load_cases(STAGED_DATASET)
    full = load_cases(CHAIN_DATASET)[4]
    assert identification.target.answer.parts[2].value == "T3=G9"
    assert identification.target.answer.parts[-1].value == "UNUSED=G4"
    assert planning.target.answer == full.target.answer
    assert planning.copy_probe is not None and full.copy_probe is not None
    assert planning.copy_probe.answer == full.copy_probe.answer
    assert [case.target.answer.legacy_value() for case in single_queries[:3]] == [
        "7;T5>T3>T4>T2",
        "11;T5>T3>T2>T8>T6",
        "11;T8>T3>T2>T5>T6",
    ]
    assert [case.target.answer.legacy_value() for case in single_queries[3:]] == [
        "11;U1>U2>U7>U5>U6",
        "11;V5>V8>V3>V4>V2",
    ]


def test_staged_verifiers_reject_codebook_drift() -> None:
    identification, planning, *_ = [
        case.model_copy(deep=True) for case in load_cases(STAGED_DATASET)
    ]
    identification.target.problem = identification.target.problem.replace(
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,h}",
        "G9=取(b,a,d,c,f,e,h,g)△{c,d,f,g}",
        1,
    )
    id_result = verify_case(identification)
    assert not id_result.passed
    assert any(
        not check.passed and check.name == "target-observation-text" for check in id_result.checks
    )

    planning.target.problem = planning.target.problem.replace("T3=G9", "T3=G4", 1)
    plan_result = verify_case(planning)
    assert not plan_result.passed
    assert any(
        not check.passed and check.name == "target-explicit-codebook"
        for check in plan_result.checks
    )


def test_q2_parameter_variants_are_exhaustively_conjugate_and_answer_distinct() -> None:
    base_catalogue = dict(L4_CATALOGUE)
    base_query = CHAIN_LEVEL_SPECS[4].target.queries[1]
    answers = set()
    queries = set()
    for variant in Q2_CONJUGATE_VARIANTS.values():
        variant_catalogue = dict(variant.problem.catalogue)
        for index in range(1, 10):
            base_transform = base_catalogue[f"G{index}"]
            transformed = variant_catalogue[f"{variant.prefix}{index}"]
            assert all(
                transformed.apply(variant.coordinate_map.apply(state))
                == variant.coordinate_map.apply(base_transform.apply(state))
                for state in range(256)
            )
        assert variant.problem.queries[0] == tuple(
            variant.coordinate_map.apply(state) for state in base_query
        )
        answers.add((variant.expected_plan.cost, variant.expected_plan.codes))
        queries.add(variant.problem.queries[0])
    assert len(answers) == 2
    assert len(queries) == 2


def test_q2_variant_verifier_rejects_conjugate_mask_drift() -> None:
    variant_case = load_cases(STAGED_DATASET)[5].model_copy(deep=True)
    assert "R9=取(g,e,h,f,b,d,a,c)△{a,c,d,g}" in variant_case.target.problem
    variant_case.target.problem = variant_case.target.problem.replace(
        "R9=取(g,e,h,f,b,d,a,c)△{a,c,d,g}",
        "R9=取(g,e,h,f,b,d,a,c)△{a,c,d,h}",
        1,
    )
    result = verify_case(variant_case)
    assert not result.passed
    assert any(not check.passed and check.name == "target-explicit-text" for check in result.checks)


def test_q2_optimality_certificates_are_strict_audited_and_verified() -> None:
    cases = load_cases(CERTIFICATE_DATASET)
    report = validate_transfer_design(cases)
    assert report.ok, report.issues
    assert [case.id for case in cases] == [
        "DIAG-P5-LATENT-L4-PLAN-Q2-CERT-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-V1-CERT-01",
        "DIAG-P5-LATENT-L4-PLAN-Q2-V2-CERT-01",
    ]
    for case in cases:
        result = verify_case(case)
        assert result.passed, result
        assert len(result.checks) == 19
        assert len(case.target.answer.parts) == 6


def test_q2_certificate_family_has_exact_path_counts() -> None:
    answers = set()
    for spec in Q2_CERTIFICATE_SPECS.values():
        certificate = _optimality_certificate(spec.problem, spec.codebook)
        assert certificate.best_cost == 11
        assert certificate.lower_goal_count == 0
        assert len(certificate.best_plans) == 1
        assert certificate.runner_up_cost == 12
        assert certificate.runner_up_count == 1
        answers.add(_format_certificate(certificate))
    assert len(answers) == 3


def test_q2_certificate_counts_match_independent_bounded_dfs() -> None:
    def first_hit_counts(spec, codebook, maximum_cost: int) -> dict[int, int]:
        transforms = dict(spec.problem.catalogue)
        semantics = dict(codebook)
        counts: dict[int, int] = {}
        initial, goal = spec.problem.queries[0]

        def visit(state: int, used: int, cost: int) -> None:
            if state == goal:
                counts[cost] = counts.get(cost, 0) + 1
                return
            for index, (code, action_cost) in enumerate(spec.problem.costs):
                next_cost = cost + action_cost
                if used & (1 << index) or next_cost > maximum_cost:
                    continue
                next_state = transforms[semantics[code]].apply(state)
                visit(next_state, used | (1 << index), next_cost)

        visit(initial, 0, 0)
        return counts

    for spec in Q2_CERTIFICATE_SPECS.values():
        assert first_hit_counts(spec, spec.codebook, 12) == {11: 1, 12: 1}
        assert first_hit_counts(spec, spec.old_codebook, 15) == {14: 1, 15: 7}


def test_q2_certificate_source_is_visible_without_target_gold_leakage() -> None:
    case = load_cases(CERTIFICATE_DATASET)[1]
    source_prompt = build_prompt(case.prompt_view(), Condition.WITH_SOURCE)
    target_prompt = build_prompt(case.prompt_view(), Condition.TARGET_ONLY)
    teaching_rule = "等成本的不同有序路径必须分别保留并计数"
    assert teaching_rule in source_prompt.user
    assert case.source.answer in source_prompt.user
    assert teaching_rule not in target_prompt.user
    assert case.source.answer not in target_prompt.user
    assert case.target.answer.legacy_value() not in source_prompt.user


def test_q2_certificate_verifier_rejects_runner_up_count_drift() -> None:
    case = load_cases(CERTIFICATE_DATASET)[2].model_copy(deep=True)
    case.target.answer.parts[-1].value = "2"
    result = verify_case(case)
    assert not result.passed
    assert any(not check.passed and check.name == "stored-target" for check in result.checks)


def test_q2_decoupled_sources_preserve_identical_targets_and_prompts() -> None:
    aligned_cases = load_cases(CERTIFICATE_DATASET)
    decoupled_cases = load_cases(DECOUPLED_CERTIFICATE_DATASET)
    assert len(decoupled_cases) == 3
    for aligned, decoupled in zip(aligned_cases, decoupled_cases, strict=True):
        result = verify_case(decoupled)
        assert result.passed, result
        assert len(result.checks) == 19
        assert aligned.target == decoupled.target
        assert aligned.source.answer != decoupled.source.answer
        assert decoupled.source.answer == "12;S3>S7>S2>S4>S5;0;1;13;5"
        aligned_prompt = build_prompt(aligned.prompt_view(), Condition.TARGET_ONLY)
        decoupled_prompt = build_prompt(decoupled.prompt_view(), Condition.TARGET_ONLY)
        assert aligned_prompt.user == decoupled_prompt.user
        assert aligned_prompt.prompt_sha256 == decoupled_prompt.prompt_sha256
