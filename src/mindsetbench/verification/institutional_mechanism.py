from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MechanismLabel(StrEnum):
    CREDIBLE_COMMITMENT = "CREDIBLE_COMMITMENT"
    SEPARATING_SIGNAL = "SEPARATING_SIGNAL"
    POOLING_SIGNAL = "POOLING_SIGNAL"
    NONCREDIBLE = "NONCREDIBLE"


@dataclass(frozen=True, slots=True)
class MechanismCase:
    observed_before_response: bool
    removes_defection_option: bool = False
    costly_action: bool = False
    actor_bears_cost: bool = False
    committed_type_can_bear: bool = False
    opportunistic_type_can_bear: bool = False
    third_party_reimbursement: bool = False


def classify_mechanism(case: MechanismCase) -> MechanismLabel:
    """Classify the mechanism by timing, option removal, and effective cost incidence."""

    if not case.observed_before_response:
        return MechanismLabel.NONCREDIBLE
    if case.removes_defection_option:
        return MechanismLabel.CREDIBLE_COMMITMENT
    if not case.costly_action or not case.committed_type_can_bear:
        return MechanismLabel.NONCREDIBLE

    effectively_self_funded = case.actor_bears_cost and not case.third_party_reimbursement
    opportunist_can_mimic = (
        case.opportunistic_type_can_bear
        or case.third_party_reimbursement
        or not case.actor_bears_cost
    )
    if effectively_self_funded and not opportunist_can_mimic:
        return MechanismLabel.SEPARATING_SIGNAL
    return MechanismLabel.POOLING_SIGNAL
