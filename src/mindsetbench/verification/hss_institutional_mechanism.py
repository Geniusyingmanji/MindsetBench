from __future__ import annotations

from collections.abc import Mapping, Sequence

from mindsetbench.models.case import Case
from mindsetbench.verification.base import VerificationCheck, VerificationResult
from mindsetbench.verification.institutional_mechanism import (
    MechanismCase,
    classify_mechanism,
)
from mindsetbench.verification.registry import register


def _check(name: str, actual: object, expected: object) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        passed=actual == expected,
        expected=str(expected),
        actual=str(actual),
    )


def _contains_all(text: str, phrases: Sequence[str]) -> bool:
    return all(phrase in text for phrase in phrases)


def _labels(cases: Mapping[str, MechanismCase], order: Sequence[str]) -> list[str]:
    return [f"{case_id}={classify_mechanism(cases[case_id]).value}" for case_id in order]


def _answer(cases: Mapping[str, MechanismCase], order: Sequence[str]) -> str:
    return ";".join(_labels(cases, order))


SOURCE_ORDER = ("S1", "S2", "S3", "S4")
SOURCE_REQUIRED_PHRASES = (
    "行动必须在观察者作出回应之前可核验",
    "永久删除日后背离选项",
    "由行动者实际承担且机会主义类型无法承受",
    "第三方全额补偿会让原本不能模仿的类型也能模仿",
)


def _source_cases() -> dict[str, MechanismCase]:
    return {
        "S1": MechanismCase(
            True, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
        "S2": MechanismCase(True, removes_defection_option=True),
        "S3": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
        "S4": MechanismCase(False),
    }


def _source_checks(case: Case) -> list[VerificationCheck]:
    labels = _labels(_source_cases(), SOURCE_ORDER)
    return [
        _check(
            "source-text-mechanism-conditions",
            _contains_all(case.source.problem, SOURCE_REQUIRED_PHRASES),
            True,
        ),
        _check(
            "source-mechanism-labels",
            labels,
            [
                "S1=SEPARATING_SIGNAL",
                "S2=CREDIBLE_COMMITMENT",
                "S3=POOLING_SIGNAL",
                "S4=NONCREDIBLE",
            ],
        ),
        _check("stored-source", case.source.answer, ";".join(labels)),
    ]


def _verify_case(
    case: Case,
    *,
    target_cases: Mapping[str, MechanismCase],
    lure_cases: Mapping[str, MechanismCase],
    order: Sequence[str],
    required_phrases: Sequence[str],
    expected_target: Sequence[str],
    expected_lure: Sequence[str],
) -> VerificationResult:
    target = _labels(target_cases, order)
    lure = _labels(lure_cases, order)
    assert case.lure is not None and case.lure.answer is not None
    assert case.copy_probe is not None
    checks = _source_checks(case)
    checks.extend(
        [
            _check(
                "target-text-mechanism-facts",
                _contains_all(case.target.problem, required_phrases),
                True,
            ),
            _check("target-mechanisms", target, list(expected_target)),
            _check("negative-control-mechanisms", lure, list(expected_lure)),
            _check("stored-target", case.target.answer.legacy_value(), ";".join(target)),
            _check("stored-lure", case.lure.answer.legacy_value(), ";".join(lure)),
            _check("copy-equals-lure", case.copy_probe.answer.legacy_value(), ";".join(lure)),
            _check("copy-differs-from-target", target != lure, True),
        ]
    )
    return VerificationResult(case_id=case.id, checks=checks, verifier=__name__)


@register("HSS-P8-INST-MECHANISM-L0-01")
def verify_hss_p8_inst_mechanism_l0_01(case: Case) -> VerificationResult:
    target = {
        "M1": MechanismCase(
            True, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
        "M2": MechanismCase(True, removes_defection_option=True),
        "M3": MechanismCase(False),
    }
    lure = dict(target)
    lure["M1"] = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
        third_party_reimbursement=True,
    )
    return _verify_case(
        case,
        target_cases=target,
        lure_cases=lure,
        order=("M1", "M2", "M3"),
        required_phrases=(
            "保证金由卖家自己承担且不获补偿",
            "可靠卖家能够承担而机会主义卖家不能",
            "在买家决定前永久删除撤单密钥",
            "声明发布在买家完成选择之后",
        ),
        expected_target=(
            "M1=SEPARATING_SIGNAL",
            "M2=CREDIBLE_COMMITMENT",
            "M3=NONCREDIBLE",
        ),
        expected_lure=(
            "M1=POOLING_SIGNAL",
            "M2=CREDIBLE_COMMITMENT",
            "M3=NONCREDIBLE",
        ),
    )


@register("HSS-P8-INST-MECHANISM-L1-01")
def verify_hss_p8_inst_mechanism_l1_01(case: Case) -> VerificationResult:
    target = {
        "K1": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
        "K2": MechanismCase(True, removes_defection_option=True),
        "K3": MechanismCase(
            False, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
    }
    lure = dict(target)
    lure["K1"] = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
        opportunistic_type_can_bear=False,
    )
    return _verify_case(
        case,
        target_cases=target,
        lure_cases=lure,
        order=("K1", "K2", "K3"),
        required_phrases=(
            "两类供应商都能轻易购买",
            "在采购决定前把改单权不可撤销地交给独立托管人",
            "高价展示发生在合同已经授予之后",
        ),
        expected_target=(
            "K1=POOLING_SIGNAL",
            "K2=CREDIBLE_COMMITMENT",
            "K3=NONCREDIBLE",
        ),
        expected_lure=(
            "K1=SEPARATING_SIGNAL",
            "K2=CREDIBLE_COMMITMENT",
            "K3=NONCREDIBLE",
        ),
    )


@register("HSS-P8-INST-MECHANISM-L2-01")
def verify_hss_p8_inst_mechanism_l2_01(case: Case) -> VerificationResult:
    target = {
        "L1": MechanismCase(
            True, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
        "L2": MechanismCase(True, removes_defection_option=True),
        "L3": MechanismCase(False),
        "L4": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
    }
    lure = dict(target)
    lure["L1"] = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
        third_party_reimbursement=True,
    )
    return _verify_case(
        case,
        target_cases=target,
        lure_cases=lure,
        order=("L1", "L2", "L3", "L4"),
        required_phrases=(
            "基金由联盟自己的金库支付且不返还",
            "合作型联盟能够持续而临时套利联盟不能",
            "在表决前把单方关闭权永久交给独立信托",
            "口头保障出现在表决完成之后",
            "两类雇主都能购买同一枚合规徽章",
        ),
        expected_target=(
            "L1=SEPARATING_SIGNAL",
            "L2=CREDIBLE_COMMITMENT",
            "L3=NONCREDIBLE",
            "L4=POOLING_SIGNAL",
        ),
        expected_lure=(
            "L1=POOLING_SIGNAL",
            "L2=CREDIBLE_COMMITMENT",
            "L3=NONCREDIBLE",
            "L4=POOLING_SIGNAL",
        ),
    )


@register("HSS-P8-INST-MECHANISM-L3-01")
def verify_hss_p8_inst_mechanism_l3_01(case: Case) -> VerificationResult:
    target = {
        "R1": MechanismCase(True),
        "R2": MechanismCase(
            True, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
        "R3": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            third_party_reimbursement=True,
        ),
        "R4": MechanismCase(False),
        "R5": MechanismCase(True, removes_defection_option=True),
        "R6": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
    }
    lure = dict(target)
    lure["R1"] = MechanismCase(True, removes_defection_option=True)
    lure["R3"] = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
    )
    return _verify_case(
        case,
        target_cases=target,
        lure_cases=lure,
        order=("R1", "R2", "R3", "R4", "R5", "R6"),
        required_phrases=(
            "协会保留的认证副本可在投票后自动换发同等许可证",
            "守约协会能承担、掠夺型协会不能承担",
            "基金会为所有入选者全额报销，并预先提供过桥资金",
            "演说发生在席位分配结束后",
            "把唯一捕捞密钥交给独立保管人并销毁全部副本",
            "两类协会都能承担且都可购买",
        ),
        expected_target=(
            "R1=NONCREDIBLE",
            "R2=SEPARATING_SIGNAL",
            "R3=POOLING_SIGNAL",
            "R4=NONCREDIBLE",
            "R5=CREDIBLE_COMMITMENT",
            "R6=POOLING_SIGNAL",
        ),
        expected_lure=(
            "R1=CREDIBLE_COMMITMENT",
            "R2=SEPARATING_SIGNAL",
            "R3=SEPARATING_SIGNAL",
            "R4=NONCREDIBLE",
            "R5=CREDIBLE_COMMITMENT",
            "R6=POOLING_SIGNAL",
        ),
    )


@register("HSS-P8-INST-MECHANISM-L4-01")
def verify_hss_p8_inst_mechanism_l4_01(case: Case) -> VerificationResult:
    target = {
        "H1": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            third_party_reimbursement=True,
        ),
        "H2": MechanismCase(True),
        "H3": MechanismCase(
            False, costly_action=True, actor_bears_cost=True, committed_type_can_bear=True
        ),
        "H4": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
            opportunistic_type_can_bear=True,
        ),
        "H5": MechanismCase(
            True,
            costly_action=True,
            actor_bears_cost=True,
            committed_type_can_bear=True,
        ),
        "H6": MechanismCase(True, removes_defection_option=True),
    }
    lure = dict(target)
    lure["H1"] = MechanismCase(
        True,
        costly_action=True,
        actor_bears_cost=True,
        committed_type_can_bear=True,
    )
    lure["H2"] = MechanismCase(True, removes_defection_option=True)
    return _verify_case(
        case,
        target_cases=target,
        lure_cases=lure,
        order=("H1", "H2", "H3", "H4", "H5", "H6"),
        required_phrases=(
            "担保人向任何获准派别全额返还保证金，并为其预先垫资",
            "垫资和返还同样覆盖机会主义派别",
            "凭自己的单方书函立即复制密钥",
            "集会发生在接纳投票以后",
            "两类派别都能取得同一种公开印章",
            "任何赞助人或保险都不得补偿",
            "不存在副本、补发或代理加入渠道",
        ),
        expected_target=(
            "H1=POOLING_SIGNAL",
            "H2=NONCREDIBLE",
            "H3=NONCREDIBLE",
            "H4=POOLING_SIGNAL",
            "H5=SEPARATING_SIGNAL",
            "H6=CREDIBLE_COMMITMENT",
        ),
        expected_lure=(
            "H1=SEPARATING_SIGNAL",
            "H2=CREDIBLE_COMMITMENT",
            "H3=NONCREDIBLE",
            "H4=POOLING_SIGNAL",
            "H5=SEPARATING_SIGNAL",
            "H6=CREDIBLE_COMMITMENT",
        ),
    )
