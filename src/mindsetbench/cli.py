from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from mindsetbench.data import (
    PROJECT_ROOT,
    load_cases,
    load_manifest,
    load_schema_cards,
    validate_dataset,
    validate_schema_cards,
)
from mindsetbench.data.loader import DEFAULT_DATASET, index_cases
from mindsetbench.grading import grade_response
from mindsetbench.metrics import assess_calibration, summarize_slices, summarize_transfer
from mindsetbench.models.case import Case
from mindsetbench.models.prompt import Condition, PromptContext
from mindsetbench.prompting import build_prompt, condition_is_applicable
from mindsetbench.runner import (
    ExperimentConfig,
    MockProvider,
    OpenAICompatibleProvider,
    ProviderError,
    ResultStore,
    run_experiment,
)
from mindsetbench.verification import registered_case_ids, verify_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mb", description="MindsetBench toolkit")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="validate a JSONL dataset")
    validate.add_argument("path", nargs="?", default=str(DEFAULT_DATASET))
    validate.add_argument("--strict-v1", action="store_true")

    validate_cards = subcommands.add_parser(
        "validate-cards", help="validate schema cards against a dataset"
    )
    validate_cards.add_argument("cards")
    validate_cards.add_argument("dataset")

    audit = subcommands.add_parser(
        "audit", help="audit transfer-design invariants beyond the data schema"
    )
    audit.add_argument("path")
    audit.add_argument("--require-complete-chains", action="store_true")

    schema = subcommands.add_parser("schema", help="emit the canonical JSON schema")
    schema.add_argument("--output")

    verify = subcommands.add_parser("verify", help="run executable case verifiers")
    verify.add_argument("target", nargs="?", default="all", help="case id or 'all'")
    verify.add_argument("--dataset", default=str(DEFAULT_DATASET))

    prompt = subcommands.add_parser("prompt", help="render an evaluation prompt")
    prompt.add_argument("case_id")
    prompt.add_argument("condition", choices=[condition.value for condition in Condition])
    prompt.add_argument("--dataset", default=str(DEFAULT_DATASET))
    prompt.add_argument("--reference-id")
    prompt.add_argument("--skill-file")

    grade = subcommands.add_parser("grade", help="grade a saved response")
    grade.add_argument("case_id")
    grade.add_argument("response", help="response file, or '-' for stdin")
    grade.add_argument("--dataset", default=str(DEFAULT_DATASET))
    grade.add_argument("--legacy-fallback", action="store_true")

    smoke = subcommands.add_parser("smoke", help="run the five-case vertical slice")
    smoke.add_argument("--database")

    run = subcommands.add_parser("run", help="run an experiment against a chat endpoint")
    run.add_argument("--dataset", required=True)
    run.add_argument("--database", required=True)
    run.add_argument("--experiment-id", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--endpoint", required=True)
    run.add_argument("--api-key-env", default="MINDSETBENCH_API_KEY")
    run.add_argument(
        "--conditions",
        nargs="+",
        choices=[condition.value for condition in Condition],
        default=[
            Condition.TARGET_ONLY.value,
            Condition.WITH_SOURCE.value,
            Condition.WITH_LURE.value,
        ],
    )
    run.add_argument("--samples-per-item", type=int, default=1)
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--max-output-tokens", type=int, default=2048)
    run.add_argument("--concurrency", type=int, default=4)
    run.add_argument("--max-retries", type=int, default=2)

    report = subcommands.add_parser("report", help="summarize a saved experiment database")
    report.add_argument("--database", required=True)
    report.add_argument("--experiment-id", required=True)
    report.add_argument("--calibration-gates", action="store_true")
    report.add_argument("--min-samples", type=int, default=3)

    plan_run = subcommands.add_parser(
        "plan-run", help="inspect an evaluation matrix without calling a provider"
    )
    plan_run.add_argument("--dataset", required=True)
    plan_run.add_argument(
        "--conditions",
        nargs="+",
        choices=[
            Condition.TARGET_ONLY.value,
            Condition.WITH_SOURCE.value,
            Condition.WITH_LURE.value,
        ],
        default=[
            Condition.TARGET_ONLY.value,
            Condition.WITH_SOURCE.value,
            Condition.WITH_LURE.value,
        ],
    )
    plan_run.add_argument("--samples-per-item", type=int, default=1)
    plan_run.add_argument("--max-output-tokens", type=int, default=8192)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    handlers = {
        "validate": _cmd_validate,
        "validate-cards": _cmd_validate_cards,
        "audit": _cmd_audit,
        "schema": _cmd_schema,
        "verify": _cmd_verify,
        "prompt": _cmd_prompt,
        "grade": _cmd_grade,
        "smoke": _cmd_smoke,
        "run": _cmd_run,
        "report": _cmd_report,
        "plan-run": _cmd_plan_run,
    }
    status = handlers[args.command](args)
    raise SystemExit(status or 0)


def _cmd_validate(args: argparse.Namespace) -> int:
    cases = load_cases(args.path)
    report = validate_dataset(cases, strict_v1=args.strict_v1)
    for issue in report.issues:
        case = f" [{issue.case_id}]" if issue.case_id else ""
        print(f"{issue.severity.value.upper()} {issue.code}{case}: {issue.message}")
    print(f"cases={len(cases)} errors={len(report.errors)} warnings={len(report.warnings)}")
    return 0 if report.ok else 1


def _cmd_validate_cards(args: argparse.Namespace) -> int:
    cards = load_schema_cards(args.cards)
    cases = load_cases(args.dataset)
    report = validate_schema_cards(cards, cases)
    for issue in report.issues:
        subject = f" [{issue.case_id}]" if issue.case_id else ""
        print(f"{issue.severity.value.upper()} {issue.code}{subject}: {issue.message}")
    print(f"cards={len(cards)} cases={len(cases)} errors={len(report.errors)}")
    return 0 if report.ok else 1


def _cmd_audit(args: argparse.Namespace) -> int:
    from mindsetbench.data import validate_transfer_design

    cases = load_cases(args.path)
    report = validate_transfer_design(
        cases,
        require_complete_chains=args.require_complete_chains,
    )
    for issue in report.issues:
        subject = f" [{issue.case_id}]" if issue.case_id else ""
        print(f"{issue.severity.value.upper()} {issue.code}{subject}: {issue.message}")
    print(f"cases={len(cases)} errors={len(report.errors)} warnings={len(report.warnings)}")
    return 0 if report.ok else 1


def _cmd_schema(args: argparse.Namespace) -> int:
    serialized = json.dumps(Case.model_json_schema(), ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")
        print(output)
    else:
        print(serialized)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    by_id = index_cases(load_cases(args.dataset))
    targets = sorted(registered_case_ids() & set(by_id)) if args.target == "all" else [args.target]
    if not targets:
        print("MISSING no registered verifiers for this dataset")
        return 1
    failed = 0
    for case_id in targets:
        if case_id not in by_id:
            print(f"MISSING {case_id}")
            failed += 1
            continue
        try:
            result = verify_case(by_id[case_id])
        except KeyError as exc:
            print(f"MISSING {case_id}: {exc}")
            failed += 1
            continue
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {case_id} ({len(result.checks)} checks)")
        for check in result.checks:
            if not check.passed:
                print(f"  - {check.name}: expected={check.expected} actual={check.actual}")
        failed += int(not result.passed)
    return 1 if failed else 0


def _cmd_prompt(args: argparse.Namespace) -> int:
    by_id = index_cases(load_cases(args.dataset))
    case = by_id[args.case_id]
    context = PromptContext()
    if args.reference_id:
        reference = by_id[args.reference_id]
        context = PromptContext(
            reference_case_id=reference.id,
            reference_problem=reference.source.problem,
            reference_solution=reference.source.solution,
            reference_answer=reference.source.answer,
        )
    if args.skill_file:
        context.skill_library = Path(args.skill_file).read_text(encoding="utf-8")
    artifact = build_prompt(case.prompt_view(), Condition(args.condition), context)
    print(artifact.user)
    return 0


def _cmd_grade(args: argparse.Namespace) -> int:
    by_id = index_cases(load_cases(args.dataset))
    response = (
        sys.stdin.read()
        if args.response == "-"
        else Path(args.response).read_text(encoding="utf-8")
    )
    result = grade_response(
        by_id[args.case_id].gold_view(),
        response,
        require_marker=not args.legacy_fallback,
    )
    print(result.model_dump_json(indent=2))
    return 0 if result.correct else 1


def _cmd_smoke(args: argparse.Namespace) -> int:
    if args.database:
        return asyncio.run(_run_smoke(Path(args.database)))
    with tempfile.TemporaryDirectory(prefix="mindsetbench-smoke-") as directory:
        return asyncio.run(_run_smoke(Path(directory) / "results.sqlite"))


def _cmd_run(args: argparse.Namespace) -> int:
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"missing API key environment variable: {args.api_key_env}", file=sys.stderr)
        return 2
    cases = load_cases(args.dataset)
    report = validate_dataset(cases, strict_v1=True)
    if not report.ok:
        for issue in report.errors:
            print(f"ERROR {issue.code} [{issue.case_id}]: {issue.message}", file=sys.stderr)
        return 1

    config = ExperimentConfig(
        experiment_id=args.experiment_id,
        model=args.model,
        conditions=[Condition(value) for value in args.conditions],
        samples_per_item=args.samples_per_item,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        concurrency=args.concurrency,
        max_retries=args.max_retries,
    )
    provider = OpenAICompatibleProvider(args.endpoint, api_key)
    with ResultStore(args.database) as store:
        try:
            new_records = asyncio.run(run_experiment(cases, config, provider, store))
        except ProviderError as exc:
            partial_count = store.trial_count(config.experiment_id)
            print(f"provider error: {exc}", file=sys.stderr)
            print(f"partial_trials_saved={partial_count}", file=sys.stderr)
            return 3
        except ValueError as exc:
            print(f"run configuration error: {exc}", file=sys.stderr)
            return 2
        records = store.load_trials(config.experiment_id)
    print(
        json.dumps(
            {
                "new_trials": len(new_records),
                **summarize_transfer(records),
                **summarize_slices(records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    database = Path(args.database)
    if not database.exists():
        print(f"result database does not exist: {database}", file=sys.stderr)
        return 2
    with ResultStore(database) as store:
        records = store.load_trials(args.experiment_id)
    if not records:
        print(f"no trials found for experiment: {args.experiment_id}", file=sys.stderr)
        return 1
    output: dict[str, object] = {
        **summarize_transfer(records),
        **summarize_slices(records),
    }
    if args.calibration_gates:
        output["calibration"] = assess_calibration(
            records,
            min_samples_per_case_condition=args.min_samples,
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def _cmd_plan_run(args: argparse.Namespace) -> int:
    if args.samples_per_item < 1 or args.max_output_tokens < 1:
        print("samples-per-item and max-output-tokens must be positive", file=sys.stderr)
        return 2
    cases = load_cases(args.dataset)
    validation = validate_dataset(cases, strict_v1=True)
    if not validation.ok:
        for issue in validation.errors:
            print(f"ERROR {issue.code} [{issue.case_id}]: {issue.message}", file=sys.stderr)
        return 1
    conditions = [Condition(value) for value in args.conditions]
    prompt_lengths: dict[str, list[int]] = defaultdict(list)
    trial_counts: Counter[str] = Counter()
    paradigm_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    for case in cases:
        for condition in conditions:
            if not condition_is_applicable(case.prompt_view(), condition):
                continue
            prompt = build_prompt(case.prompt_view(), condition)
            prompt_lengths[condition.value].append(len(prompt.system) + len(prompt.user))
            trial_counts[condition.value] += args.samples_per_item
            paradigm_counts[case.paradigm.value] += args.samples_per_item
            level_counts[str(case.level)] += args.samples_per_item
    total_trials = sum(trial_counts.values())
    output = {
        "cases": len(cases),
        "samples_per_item": args.samples_per_item,
        "max_output_tokens_per_trial": args.max_output_tokens,
        "total_trials": total_trials,
        "maximum_completion_token_budget": total_trials * args.max_output_tokens,
        "trials_by_condition": dict(sorted(trial_counts.items())),
        "trials_by_paradigm": dict(sorted(paradigm_counts.items())),
        "trials_by_level": dict(sorted(level_counts.items())),
        "prompt_chars_by_condition": {
            condition: {
                "min": min(lengths),
                "mean": mean(lengths),
                "max": max(lengths),
            }
            for condition, lengths in sorted(prompt_lengths.items())
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


async def _run_smoke(database: Path) -> int:
    manifest = PROJECT_ROOT / "data" / "manifests" / "smoke.json"
    cases = load_manifest(manifest)
    validation = validate_dataset(cases)
    verification = [verify_case(case) for case in cases]
    if validation.errors or any(not result.passed for result in verification):
        print("smoke preflight failed", file=sys.stderr)
        return 1

    target_answers = {case.id: case.target.answer.legacy_value() for case in cases}
    responses: dict[str, str] = {}
    for case in cases:
        correct = f"推理略。\nANSWER: {target_answers[case.id]}"
        responses[f"{case.id}|with-source"] = correct
        if case.level <= 2:
            responses[f"{case.id}|target-only"] = correct
            responses[f"{case.id}|random-source"] = correct
        else:
            wrong = "6" if case.id == "L3-A-01" else "S3"
            responses[f"{case.id}|target-only"] = f"推理略。\nANSWER: {wrong}"
            responses[f"{case.id}|random-source"] = f"推理略。\nANSWER: {wrong}"
    responses.update(
        {
            "L2-F-05|with-lure": "ANSWER: 15.5",
            "L3-A-01|with-lure": "ANSWER: 6",
            "L4-F-01|with-lure": "ANSWER: S3",
        }
    )

    config = ExperimentConfig(
        experiment_id="vertical-slice-v1",
        model="mock-model",
        conditions=[
            Condition.TARGET_ONLY,
            Condition.RANDOM_SOURCE,
            Condition.WITH_LURE,
            Condition.WITH_SOURCE,
        ],
        samples_per_item=1,
        seed=20260831,
    )
    provider = MockProvider(responses)
    with ResultStore(database) as store:
        first = await run_experiment(cases, config, provider, store)
        second = await run_experiment(cases, config, provider, store)
        records = store.load_trials(config.experiment_id)
        summary = summarize_transfer(records)

    output = {
        "validation_warnings": len(validation.warnings),
        "verifiers_passed": sum(result.passed for result in verification),
        "new_trials": len(first),
        "resume_new_trials": len(second),
        "provider_calls": provider.call_count,
        **summary,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    expected = len(records) == 18 and len(second) == 0 and provider.call_count == 18
    return 0 if expected else 1


if __name__ == "__main__":
    main()
