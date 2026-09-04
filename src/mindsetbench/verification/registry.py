from __future__ import annotations

from collections.abc import Callable

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationResult

Verifier = Callable[[Case], VerificationResult]
_REGISTRY: dict[str, Verifier] = {}


def register(case_id: str) -> Callable[[Verifier], Verifier]:
    def decorator(function: Verifier) -> Verifier:
        if case_id in _REGISTRY:
            raise RuntimeError(f"duplicate verifier registration: {case_id}")
        _REGISTRY[case_id] = function
        return function

    return decorator


def registered_case_ids() -> set[str]:
    _load_builtin_verifiers()
    return set(_REGISTRY)


def verify_case(case: Case) -> VerificationResult:
    _load_builtin_verifiers()
    try:
        verifier = _REGISTRY[case.id]
    except KeyError as exc:
        raise KeyError(f"no executable verifier registered for {case.id}") from exc
    return verifier(case)


def _load_builtin_verifiers() -> None:
    # Import side effects populate the registry. Kept lazy so package imports stay cheap.
    from mindsetbench.verification import (  # noqa: F401
        expansion_cases,
        far_credible_commitment,
        far_delayed_feedback,
        far_evidence_independence,
        far_horizon_exploration,
        far_invariant_reachability,
        far_negative_evidence,
        far_scaling_law,
        far_selection_association,
        far_selection_extreme,
        far_threshold_cascade,
        formal_p2_chain,
        formal_p3_chain,
        formal_p4_chain,
        formal_p5_certificate,
        formal_p5_certificate_outage,
        formal_p5_certificate_policy,
        formal_p5_chain,
        formal_p5_latent,
        formal_p6_chain,
        hard_seeds,
        hss_active_query,
        hss_adaptive_policy,
        hss_argument_evidence,
        hss_historical_analogy,
        hss_institutional_mechanism,
        hss_norm_precedent,
        smoke_cases,
    )
