import pytest

from havengrid.domain.enums import CaseAction, CaseState, VerificationOutcome
from havengrid.domain.errors import IllegalTransition
from havengrid.kernel.state_machine import TRANSITIONS, legal_actions, next_state
from tests.conftest import run_to_batch_matched, run_to_proposed, run_to_recalculated

S, A = CaseState, CaseAction


def test_happy_path_table_is_exactly_the_documented_lifecycle():
    path = [
        (S.FORECASTED, A.PROPOSE, S.INTERVENTION_PROPOSED),
        (S.INTERVENTION_PROPOSED, A.SUBMIT_EVIDENCE, S.AWAITING_EVIDENCE_CONFIRMATION),
        (S.AWAITING_EVIDENCE_CONFIRMATION, A.CONFIRM_EVIDENCE, S.EVIDENCE_CONFIRMED),
        (S.EVIDENCE_CONFIRMED, A.INVALIDATE_PLAN, S.PLAN_INVALIDATED),
        (S.PLAN_INVALIDATED, A.RECALCULATE_PLAN, S.PLAN_RECALCULATED),
        (S.PLAN_RECALCULATED, A.APPROVE, S.APPROVED),
        (S.APPROVED, A.DISPATCH, S.DISPATCHED),
        (S.DISPATCHED, A.VERIFY_SOURCE, S.SOURCE_VERIFIED),
        (S.SOURCE_VERIFIED, A.VERIFY_DESTINATION, S.DESTINATION_VERIFIED),
        (S.DESTINATION_VERIFIED, A.VERIFY_BATCH, S.BATCH_MATCHED),
        (S.BATCH_MATCHED, A.RECONCILE, S.COVERAGE_RESTORED),
        (S.COVERAGE_RESTORED, A.CARE_DELIVERY, S.CARE_PROTECTED),
        (S.CARE_PROTECTED, A.CLOSE, S.CLOSED),
    ]
    for frm, act, to in path:
        assert next_state(frm, act) is to


@pytest.mark.parametrize("state,action", [
    (S.DISPATCHED, A.CLOSE),
    (S.DESTINATION_VERIFIED, A.CLOSE),
    (S.DESTINATION_VERIFIED, A.RECONCILE),
    (S.AWAITING_EVIDENCE_CONFIRMATION, A.CLOSE),
    (S.INTERVENTION_PROPOSED, A.DISPATCH),
    (S.APPROVED, A.VERIFY_SOURCE),
    (S.DISPATCHED, A.VERIFY_DESTINATION),
    (S.BATCH_MATCHED, A.CLOSE),
    (S.CLOSED, A.PROPOSE),
    (S.FORECASTED, A.APPROVE),
])
def test_illegal_transitions_raise(state, action):
    with pytest.raises(IllegalTransition):
        next_state(state, action)


def test_there_is_no_action_that_asserts_care_protected():
    assert not any(a.value.startswith("assert") for a in CaseAction)
    assert all(a is A.CARE_DELIVERY for (s, a), to in TRANSITIONS.items() if to is S.CARE_PROTECTED)


def test_closed_is_terminal():
    assert legal_actions(S.CLOSED, include_system=True) == []


def test_system_actions_hidden_from_public_legal_actions():
    assert A.INVALIDATE_PLAN not in legal_actions(S.EVIDENCE_CONFIRMED)
    assert A.INVALIDATE_PLAN in legal_actions(S.EVIDENCE_CONFIRMED, include_system=True)


def test_service_rejects_external_system_actions(svc, case_id):
    run_to_proposed(svc)
    with pytest.raises(IllegalTransition):
        svc.advance(case_id, A.INVALIDATE_PLAN, {})


def test_service_rejects_asserted_reconcile_outcome(svc, case_id):
    run_to_batch_matched(svc)
    with pytest.raises(IllegalTransition):
        svc.advance(case_id, A.RECONCILE, {"care_protected": True})


def test_approve_requires_a_feasible_plan(svc, case_id):
    run_to_recalculated(svc)
    assert svc.approve(case_id, approved_by="dmo").state is S.APPROVED


def test_idempotent_commands_do_not_double_apply(svc, case_id):
    a = svc.propose(case_id, command_id="cmd-1")
    b = svc.propose(case_id, command_id="cmd-1")
    assert a.state is b.state is S.INTERVENTION_PROPOSED
    assert len([x for x in svc.repo.audit_for(case_id) if x.action == "propose"]) == 1
    with pytest.raises(IllegalTransition):
        svc.propose(case_id)  # a genuinely new command in the wrong state still fails
