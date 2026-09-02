from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence

from mindsetbench.grading import grade_response
from mindsetbench.models.case import Case
from mindsetbench.models.prompt import Condition, PromptContext
from mindsetbench.models.run import ModelRequest, TrialRecord
from mindsetbench.prompting import build_prompt, condition_is_applicable
from mindsetbench.runner.config import ExperimentConfig
from mindsetbench.runner.providers import Provider, ProviderError
from mindsetbench.runner.store import ResultStore


async def run_experiment(
    cases: Sequence[Case],
    config: ExperimentConfig,
    provider: Provider,
    store: ResultStore,
) -> list[TrialRecord]:
    store.register_experiment(config)
    semaphore = asyncio.Semaphore(config.concurrency)
    pending: list[tuple[Case, Condition, int]] = []
    for case in cases:
        for condition in config.conditions:
            if not condition_is_applicable(case.prompt_view(), condition):
                continue
            for sample_index in range(config.samples_per_item):
                if store.has_trial(
                    config.experiment_id,
                    config.model,
                    case.id,
                    condition,
                    sample_index,
                ):
                    continue
                pending.append((case, condition, sample_index))
    if not pending:
        return []

    # Validate auth, model support, and provider parameters with one real trial before
    # fanning out. A permanent provider failure therefore consumes one request, not
    # an entire concurrency batch, while the successful preflight remains a normal trial.
    first_case, first_condition, first_sample_index = pending[0]
    first_result = await _run_trial(
        first_case,
        cases,
        first_condition,
        first_sample_index,
        config,
        provider,
        store,
        semaphore,
    )
    jobs = [
        _run_trial(
            case,
            cases,
            condition,
            sample_index,
            config,
            provider,
            store,
            semaphore,
        )
        for case, condition, sample_index in pending[1:]
    ]
    results = [first_result, *(await asyncio.gather(*jobs))] if jobs else [first_result]
    return [result for result in results if result is not None]


async def _run_trial(
    case: Case,
    pool: Sequence[Case],
    condition: Condition,
    sample_index: int,
    config: ExperimentConfig,
    provider: Provider,
    store: ResultStore,
    semaphore: asyncio.Semaphore,
) -> TrialRecord | None:
    context = _build_context(case, pool, condition, config.seed)
    prompt = build_prompt(case.prompt_view(), condition, context)
    seed = _stable_seed(config.seed, case.id, condition.value, sample_index)
    request = ModelRequest(
        model=config.model,
        prompt=prompt,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        seed=seed,
        metadata={"case_id": case.id, "condition": condition.value, "sample_index": sample_index},
    )

    async with semaphore:
        response = await _generate_with_retry(provider, request, config.max_retries)
    grade = grade_response(case.gold_view(), response.text)
    assert case.schema_id is not None
    record = TrialRecord(
        experiment_id=config.experiment_id,
        case_id=case.id,
        schema_id=case.schema_id,
        level=case.level,
        paradigm=case.paradigm.value,
        model=config.model,
        condition=condition,
        sample_index=sample_index,
        seed=seed,
        prompt=prompt,
        response=response,
        grade=grade,
        has_copy_probe=case.copy_probe is not None,
    )
    return record if store.save_trial(record) else None


async def _generate_with_retry(
    provider: Provider,
    request: ModelRequest,
    max_retries: int,
):
    for attempt in range(max_retries + 1):
        try:
            return await provider.generate(request)
        except Exception as exc:
            permanent_provider_error = isinstance(exc, ProviderError) and not exc.retryable
            if permanent_provider_error or attempt >= max_retries:
                raise
            await asyncio.sleep(min(2**attempt, 8))
    raise AssertionError("unreachable")


def _build_context(
    case: Case,
    pool: Sequence[Case],
    condition: Condition,
    seed: int,
) -> PromptContext:
    if condition != Condition.RANDOM_SOURCE:
        return PromptContext()
    candidates = [
        candidate
        for candidate in pool
        if candidate.id != case.id
        and candidate.schema_id != case.schema_id
        and candidate.paradigm == case.paradigm
    ]
    if not candidates:
        raise ValueError(f"no unrelated reference candidate available for {case.id}")
    candidates.sort(
        key=lambda candidate: (
            abs(candidate.level - case.level),
            abs(len(candidate.source.problem) - len(case.source.problem)),
            candidate.id,
        )
    )
    candidates = candidates[: min(3, len(candidates))]
    digest = hashlib.sha256(f"{seed}:{case.id}".encode()).digest()
    selected = candidates[int.from_bytes(digest[:8], "big") % len(candidates)]
    return PromptContext(
        reference_case_id=selected.id,
        reference_problem=selected.source.problem,
        reference_solution=selected.source.solution,
        reference_answer=selected.source.answer,
    )


def _stable_seed(base: int, case_id: str, condition: str, sample_index: int) -> int:
    digest = hashlib.sha256(f"{base}:{case_id}:{condition}:{sample_index}".encode()).digest()
    return int.from_bytes(digest[:4], "big")
