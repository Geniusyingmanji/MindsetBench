import asyncio
import json

import pytest

from mindsetbench.cli import main
from mindsetbench.data import PROJECT_ROOT, load_cases, load_manifest
from mindsetbench.metrics import summarize_transfer
from mindsetbench.models.prompt import Condition
from mindsetbench.models.run import ModelRequest, ModelResponse
from mindsetbench.prompting import build_prompt
from mindsetbench.runner import (
    ExperimentConfig,
    MockProvider,
    ReplayProvider,
    ResultStore,
    run_experiment,
)
from mindsetbench.runner.providers import ProviderError


def test_runner_is_resumable(tmp_path) -> None:
    cases = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")
    responses = {case.id: f"ANSWER: {case.target.answer.legacy_value()}" for case in cases}
    provider = MockProvider(responses)
    config = ExperimentConfig(
        experiment_id="test-resume",
        model="mock",
        conditions=[Condition.TARGET_ONLY],
        samples_per_item=1,
    )
    with ResultStore(tmp_path / "results.sqlite") as store:
        first = asyncio.run(run_experiment(cases, config, provider, store))
        second = asyncio.run(run_experiment(cases, config, provider, store))
        records = store.load_trials(config.experiment_id)

    assert len(first) == 5
    assert second == []
    assert provider.call_count == 5
    assert summarize_transfer(records)["accuracy"]["target-only"] == 1.0


def test_experiment_id_cannot_change_config(tmp_path) -> None:
    first = ExperimentConfig(
        experiment_id="same-id", model="model-a", conditions=[Condition.TARGET_ONLY]
    )
    second = first.model_copy(update={"model": "model-b"})
    with ResultStore(tmp_path / "results.sqlite") as store:
        store.register_experiment(first)
        try:
            store.register_experiment(second)
        except ValueError as exc:
            assert "different config" in str(exc)
        else:
            raise AssertionError("changed config was accepted")


def test_experiment_registration_accepts_legacy_config_defaults(tmp_path) -> None:
    config = ExperimentConfig(
        experiment_id="legacy-config",
        model="model-a",
        conditions=[Condition.TARGET_ONLY],
    )
    legacy = json.loads(config.model_dump_json())
    legacy.pop("request_timeout_seconds")
    with ResultStore(tmp_path / "legacy.sqlite") as store:
        store._connection.execute(
            "INSERT INTO experiments(experiment_id, config_json) VALUES (?, ?)",
            (config.experiment_id, json.dumps(legacy)),
        )
        store._connection.commit()
        store.register_experiment(config)


def test_replay_provider_reads_existing_pilot() -> None:
    cases = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")
    case = next(case for case in cases if case.id == "L1-A-C1")
    prompt = build_prompt(case.prompt_view(), Condition.TARGET_ONLY)
    request = ModelRequest(
        model="replay",
        prompt=prompt,
        metadata={"sample_index": 0},
    )
    provider = ReplayProvider.from_jsonl(
        PROJECT_ROOT / "harness" / "results" / "pilot-results.jsonl"
    )
    response = asyncio.run(provider.generate(request))
    assert response.text == "ANSWER: 48"


class _FailingProvider:
    def __init__(self, *, retryable: bool, failures: int):
        self.retryable = retryable
        self.failures = failures
        self.call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.call_count += 1
        if self.call_count <= self.failures:
            raise ProviderError("safe test failure", retryable=self.retryable)
        return ModelResponse(text="ANSWER: 48", model=request.model)


def test_permanent_provider_error_is_not_retried(tmp_path) -> None:
    case = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")[1]
    provider = _FailingProvider(retryable=False, failures=1)
    config = ExperimentConfig(
        experiment_id="permanent-error",
        model="mock",
        conditions=[Condition.TARGET_ONLY],
        max_retries=2,
    )
    with ResultStore(tmp_path / "permanent.sqlite") as store:
        with pytest.raises(ProviderError, match="safe test failure"):
            asyncio.run(run_experiment([case], config, provider, store))
        assert store.trial_count(config.experiment_id) == 0
    assert provider.call_count == 1


def test_retryable_provider_error_uses_configured_retries(tmp_path) -> None:
    case = load_manifest(PROJECT_ROOT / "data" / "manifests" / "smoke.json")[1]
    provider = _FailingProvider(retryable=True, failures=2)
    config = ExperimentConfig(
        experiment_id="transient-error",
        model="mock",
        conditions=[Condition.TARGET_ONLY],
        max_retries=2,
    )
    with ResultStore(tmp_path / "transient.sqlite") as store:
        records = asyncio.run(run_experiment([case], config, provider, store))
    assert len(records) == 1
    assert records[0].grade.correct
    assert provider.call_count == 3


def test_report_command_reloads_saved_trials_and_applies_gates(tmp_path, capsys) -> None:
    case = load_cases(PROJECT_ROOT / "data" / "v1" / "formal-p3-causal-chain.yaml")[3]
    database = tmp_path / "report.sqlite"
    provider = MockProvider({case.id: f"ANSWER: {case.target.answer.legacy_value()}"})
    config = ExperimentConfig(
        experiment_id="report-test",
        model="mock",
        conditions=[
            Condition.TARGET_ONLY,
            Condition.WITH_SOURCE,
            Condition.WITH_LURE,
        ],
        samples_per_item=3,
    )
    with ResultStore(database) as store:
        asyncio.run(run_experiment([case], config, provider, store))

    with pytest.raises(SystemExit) as exit_info:
        main(
            [
                "report",
                "--database",
                str(database),
                "--experiment-id",
                config.experiment_id,
                "--calibration-gates",
            ]
        )
    assert exit_info.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["trials"] == 9
    assert report["calibration"]["P3"]["reasons"] == [
        "target-outside-window",
        "source-gain-below-threshold",
        "nonpositive-structural-selectivity",
    ]


def test_run_command_surfaces_provider_error_without_traceback(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    class PermanentProvider:
        call_count = 0

        async def generate(self, _request):
            self.call_count += 1
            raise ProviderError("access denied", retryable=False)

    provider = PermanentProvider()
    monkeypatch.setenv("TEST_MINDSETBENCH_KEY", "placeholder")
    provider_kwargs = {}

    def provider_factory(*_args, **kwargs):
        provider_kwargs.update(kwargs)
        return provider

    monkeypatch.setattr("mindsetbench.cli.OpenAICompatibleProvider", provider_factory)
    with pytest.raises(SystemExit) as exit_info:
        main(
            [
                "run",
                "--dataset",
                str(PROJECT_ROOT / "data" / "manifests" / "formal-new-high.json"),
                "--database",
                str(tmp_path / "failed.sqlite"),
                "--experiment-id",
                "failed-run",
                "--model",
                "mock",
                "--endpoint",
                "https://example.test/v1/chat/completions",
                "--api-key-env",
                "TEST_MINDSETBENCH_KEY",
                "--conditions",
                "target-only",
                "--concurrency",
                "1",
                "--max-retries",
                "2",
                "--request-timeout-seconds",
                "42",
            ]
        )
    assert exit_info.value.code == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "provider error: access denied" in captured.err
    assert "partial_trials_saved=0" in captured.err
    assert "Traceback" not in captured.err
    assert provider.call_count == 1
    assert provider_kwargs["timeout_seconds"] == 42


def test_run_command_surfaces_resume_config_drift_without_traceback(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    database = tmp_path / "config-drift.sqlite"
    existing = ExperimentConfig(
        experiment_id="same-run",
        model="mock",
        conditions=[Condition.TARGET_ONLY],
        concurrency=2,
    )
    with ResultStore(database) as store:
        store.register_experiment(existing)

    monkeypatch.setenv("TEST_MINDSETBENCH_KEY", "placeholder")
    with pytest.raises(SystemExit) as exit_info:
        main(
            [
                "run",
                "--dataset",
                str(PROJECT_ROOT / "data" / "manifests" / "formal-p5-high.json"),
                "--database",
                str(database),
                "--experiment-id",
                "same-run",
                "--model",
                "mock",
                "--endpoint",
                "https://example.test/v1/chat/completions",
                "--api-key-env",
                "TEST_MINDSETBENCH_KEY",
                "--conditions",
                "target-only",
                "--concurrency",
                "1",
            ]
        )
    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "run configuration error:" in captured.err
    assert "different config" in captured.err
    assert "Traceback" not in captured.err


def test_plan_run_reports_high_level_paired_matrix_without_api(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(
            [
                "plan-run",
                "--dataset",
                str(PROJECT_ROOT / "data" / "manifests" / "formal-new-high.json"),
                "--samples-per-item",
                "3",
                "--max-output-tokens",
                "8192",
            ]
        )
    assert exit_info.value.code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["cases"] == 8
    assert plan["total_trials"] == 72
    assert plan["trials_by_condition"] == {
        "target-only": 24,
        "with-lure": 24,
        "with-source": 24,
    }
    assert plan["trials_by_paradigm"] == {
        "P3": 18,
        "P4": 18,
        "P5": 18,
        "P6": 18,
    }
    assert plan["trials_by_level"] == {"3": 36, "4": 36}
    assert plan["maximum_completion_token_budget"] == 72 * 8192
