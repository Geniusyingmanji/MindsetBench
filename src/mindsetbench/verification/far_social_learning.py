"""Verifier for far-domain sequential social-learning cases.

Public actions are endogenous summaries of private signals. Once public odds are
strong enough that either private signal induces the same action, that action has
likelihood ratio one and must not be counted as another independent observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.registry import register

F = Fraction
HALF = F(1, 2)
VERIFIER = "far_social_learning"


@dataclass(frozen=True)
class ActionUpdate:
    informative: bool
    odds_after: Fraction


def _chooses_positive(
    odds: Fraction,
    accuracy: Fraction,
    signal_positive: bool,
    threshold: Fraction = HALF,
) -> bool:
    likelihood_ratio = accuracy / (1 - accuracy)
    posterior_odds = odds * (likelihood_ratio if signal_positive else 1 / likelihood_ratio)
    posterior = posterior_odds / (1 + posterior_odds)
    if posterior == threshold:
        return signal_positive
    return posterior > threshold


def observe_positive_action(
    odds: Fraction, accuracy: Fraction, threshold: Fraction = HALF
) -> ActionUpdate:
    probability = {}
    for state_true in (True, False):
        total = F(0)
        for signal_positive in (True, False):
            signal_matches = signal_positive == state_true
            signal_probability = accuracy if signal_matches else 1 - accuracy
            if _chooses_positive(odds, accuracy, signal_positive, threshold):
                total += signal_probability
        probability[state_true] = total
    informative = probability[True] != probability[False]
    return ActionUpdate(
        informative=informative,
        odds_after=odds * probability[True] / probability[False],
    )


def positive_sequence(
    accuracies: tuple[Fraction, ...],
    prior_true: Fraction = HALF,
    thresholds: tuple[Fraction, ...] | None = None,
) -> tuple[int, Fraction]:
    odds = prior_true / (1 - prior_true)
    informative = 0
    active_thresholds = thresholds or (HALF,) * len(accuracies)
    if len(active_thresholds) != len(accuracies):
        raise ValueError("accuracies and thresholds must have equal length")
    for accuracy, threshold in zip(accuracies, active_thresholds, strict=True):
        update = observe_positive_action(odds, accuracy, threshold)
        informative += int(update.informative)
        odds = update.odds_after
    return informative, odds / (1 + odds)


def sealed_positive_posterior(
    accuracies: tuple[Fraction, ...], prior_true: Fraction = HALF
) -> Fraction:
    odds = prior_true / (1 - prior_true)
    for accuracy in accuracies:
        odds *= accuracy / (1 - accuracy)
    return odds / (1 + odds)


def _signal_probability(signal: bool, state: bool, accuracy: Fraction) -> Fraction:
    return accuracy if signal == state else 1 - accuracy


def _private_action(
    common: bool,
    private_a: bool,
    private_b: bool,
    *,
    common_accuracy: Fraction,
    private_accuracy: Fraction,
) -> bool:
    odds = F(1)
    for accuracy, signal in (
        (common_accuracy, common),
        (private_accuracy, private_a),
        (private_accuracy, private_b),
    ):
        likelihood_ratio = accuracy / (1 - accuracy)
        odds *= likelihood_ratio if signal else 1 / likelihood_ratio
    return odds > 1


def joint_positive_action_likelihood(
    state: bool,
    *,
    common_accuracy: Fraction,
    private_accuracy: Fraction,
) -> Fraction:
    """Return P(two positive actions | state) when both share one signal."""
    likelihood = F(0)
    for common, a1, a2, b1, b2 in product((False, True), repeat=5):
        probability = _signal_probability(common, state, common_accuracy)
        for signal in (a1, a2, b1, b2):
            probability *= _signal_probability(signal, state, private_accuracy)
        first_positive = _private_action(
            common,
            a1,
            a2,
            common_accuracy=common_accuracy,
            private_accuracy=private_accuracy,
        )
        second_positive = _private_action(
            common,
            b1,
            b2,
            common_accuracy=common_accuracy,
            private_accuracy=private_accuracy,
        )
        if first_positive and second_positive:
            likelihood += probability
    return likelihood


def marginal_positive_action_likelihood(
    state: bool,
    *,
    common_accuracy: Fraction,
    private_accuracy: Fraction,
) -> Fraction:
    likelihood = F(0)
    for common, private_a, private_b in product((False, True), repeat=3):
        probability = _signal_probability(common, state, common_accuracy)
        probability *= _signal_probability(private_a, state, private_accuracy)
        probability *= _signal_probability(private_b, state, private_accuracy)
        if _private_action(
            common,
            private_a,
            private_b,
            common_accuracy=common_accuracy,
            private_accuracy=private_accuracy,
        ):
            likelihood += probability
    return likelihood


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _four_places(value: Fraction) -> str:
    return f"{float(value):.4f}"


SOURCE_ACCURACIES = (F(7, 10),) * 4
TARGET_ACCURACIES = (F(7, 10), F(7, 10), F(9, 10), F(7, 10))
HIGH_BAR_THRESHOLDS = (HALF, HALF, HALF, F(99, 100))
TARGET_PHRASES = (
    "事前各占一半",
    "前两位和第四位",
    "90%",
    "看得到前面已公布的表决",
    "认为真实",
)


@register("FAR-HARD-SOCIAL-LEARNING-L4-01")
def verify_social_learning(case: Case) -> VerificationResult:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None

    source_count, source_posterior = positive_sequence(SOURCE_ACCURACIES)
    count, posterior = positive_sequence(TARGET_ACCURACIES)
    sealed = sealed_positive_posterior(TARGET_ACCURACIES)

    source_answer = f"{source_count};{_four_places(source_posterior)}"
    gold = f"INFORMATIVE={count};POSTERIOR={_four_places(posterior)}"
    decoy = f"INFORMATIVE=4;POSTERIOR={_four_places(sealed)}"
    phrases_present = all(phrase in case.target.problem for phrase in TARGET_PHRASES)
    checks = [
        _check("source-derived-answer", source_answer, "2;0.8448"),
        _check("stored-source-answer", case.source.answer, source_answer),
        _check("target-text-carries-required-facts", phrases_present, True),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), decoy),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), decoy),
        _check("target-informative-actions", count, 3),
        _check("target-posterior", posterior, F(49, 50)),
        _check("sealed-posterior", _four_places(sealed), "0.9913"),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


@register("FAR-HARD-SOCIAL-LEARNING-L3-02")
def verify_social_learning_high_bar(case: Case) -> VerificationResult:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None

    source_count, source_posterior = positive_sequence(SOURCE_ACCURACIES)
    count, posterior = positive_sequence(TARGET_ACCURACIES, thresholds=HIGH_BAR_THRESHOLDS)
    ordinary_count, ordinary_posterior = positive_sequence(TARGET_ACCURACIES)

    source_answer = f"{source_count};{_four_places(source_posterior)}"
    gold = f"INFORMATIVE={count};POSTERIOR={_four_places(posterior)}"
    decoy = f"INFORMATIVE={ordinary_count};POSTERIOR={_four_places(ordinary_posterior)}"
    required = ("99%", "若恰好达到门槛", "第四位", "全部认为真实")
    checks = [
        _check("stored-source-answer", case.source.answer, source_answer),
        _check(
            "target-text-carries-required-facts",
            all(phrase in case.target.problem for phrase in required),
            True,
        ),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), decoy),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), decoy),
        _check("high-bar-restores-fourth-signal", count, 4),
        _check("high-bar-posterior", posterior, F(343, 346)),
        _check("ordinary-fourth-vote-uninformative", ordinary_count, 3),
        _check("ordinary-posterior", ordinary_posterior, F(49, 50)),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


@register("FAR-HARD-SOCIAL-AGGREGATION-L4-03")
def verify_social_learning_aggregation(case: Case) -> VerificationResult:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None

    field_accuracy = F(7, 10)
    expert_accuracy = F(9, 10)
    memo_if_true = 1 - (1 - field_accuracy) ** 2
    memo_if_false = 1 - field_accuracy**2
    odds_after_memo = memo_if_true / memo_if_false
    expert_update = observe_positive_action(odds_after_memo, expert_accuracy)
    posterior = expert_update.odds_after / (1 + expert_update.odds_after)

    unanimous_odds = field_accuracy**2 / (1 - field_accuracy) ** 2
    unanimous_update = observe_positive_action(unanimous_odds, expert_accuracy)
    unanimous_posterior = unanimous_update.odds_after / (1 + unanimous_update.odds_after)

    gold = f"THIRD=YES;POSTERIOR={_four_places(posterior)}"
    decoy = f"THIRD=YES;POSTERIOR={_four_places(unanimous_posterior)}"
    required = ("至少一份", "不公开两份原始记录", "70%", "90%", "公开表示支持")
    checks = [
        _check("stored-source-answer", case.source.answer, "2;0.8448"),
        _check(
            "target-text-carries-required-facts",
            all(phrase in case.target.problem for phrase in required),
            True,
        ),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), decoy),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), decoy),
        _check("or-memo-true-likelihood", memo_if_true, F(91, 100)),
        _check("or-memo-false-likelihood", memo_if_false, F(51, 100)),
        _check("third-action-remains-informative", expert_update.informative, True),
        _check("aggregated-report-posterior", posterior, F(273, 290)),
        _check("unanimous-decoy-posterior", unanimous_posterior, F(49, 50)),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)


@register("FAR-LATENT-SOCIAL-CORRELATED-L4-02")
def verify_correlated_social_actions(case: Case) -> VerificationResult:
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None

    common_accuracy = F(7, 10)
    private_accuracy = F(13, 20)
    expert_accuracy = F(9, 10)
    like_true = joint_positive_action_likelihood(
        True,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    like_false = joint_positive_action_likelihood(
        False,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    odds_after_pair = like_true / like_false
    expert_update = observe_positive_action(odds_after_pair, expert_accuracy)
    posterior = expert_update.odds_after / (1 + expert_update.odds_after)

    marginal_true = marginal_positive_action_likelihood(
        True,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    marginal_false = marginal_positive_action_likelihood(
        False,
        common_accuracy=common_accuracy,
        private_accuracy=private_accuracy,
    )
    naive_true = marginal_true**2
    naive_false = marginal_false**2
    naive_odds = naive_true / naive_false
    naive_update = observe_positive_action(naive_odds, expert_accuracy)
    naive_posterior = naive_update.odds_after / (1 + naive_update.odds_after)

    gold = (
        f"LIKE_T={_four_places(like_true)};LIKE_F={_four_places(like_false)};"
        f"PAIR_INDEPENDENT=NO;THIRD_INFORMATIVE=YES;POSTERIOR={_four_places(posterior)}"
    )
    lure = (
        f"LIKE_T={_four_places(naive_true)};LIKE_F={_four_places(naive_false)};"
        "PAIR_INDEPENDENT=YES;THIRD_INFORMATIVE=YES;"
        f"POSTERIOR={_four_places(naive_posterior)}"
    )
    required = (
        "同一份目录年代线索 C",
        "各自访谈两名",
        "条件独立",
        "公开支持 T",
        "判对率 90%",
        "后验过半规则",
    )
    checks = [
        _check("stored-source-answer", case.source.answer, "2;0.9730"),
        _check(
            "target-text-carries-shared-latent-world",
            all(phrase in case.target.problem for phrase in required),
            True,
        ),
        _check("joint-action-likelihood-true", like_true, F(94809, 160000)),
        _check("joint-action-likelihood-false", like_false, F(17689, 160000)),
        _check("third-action-is-informative", expert_update.informative, True),
        _check("posterior-after-public-actions", posterior, F(853281, 870970)),
        _check("stored-target-answer", case.target.answer.legacy_value(), gold),
        _check("stored-lure-answer", case.lure.answer.legacy_value(), lure),
        _check("stored-copy-probe", case.copy_probe.answer.legacy_value(), lure),
        _check("copy-probe-differs-from-gold", lure != gold, True),
    ]
    return VerificationResult(case_id=case.id, checks=checks, verifier=VERIFIER)
