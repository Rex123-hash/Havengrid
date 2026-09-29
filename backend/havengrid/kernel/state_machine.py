"""Explicit recovery-case lifecycle. Illegal transitions raise; nothing is implicit.

    FORECASTED ─propose─▶ INTERVENTION_PROPOSED
    INTERVENTION_PROPOSED ─submit_evidence─▶ AWAITING_EVIDENCE_CONFIRMATION
    INTERVENTION_PROPOSED ─approve─▶ APPROVED
    AWAITING_EVIDENCE_CONFIRMATION ─confirm_evidence─▶ EVIDENCE_CONFIRMED
    AWAITING_EVIDENCE_CONFIRMATION ─reject_evidence─▶ INTERVENTION_PROPOSED
    EVIDENCE_CONFIRMED ─(system) invalidate_plan─▶ PLAN_INVALIDATED
    EVIDENCE_CONFIRMED ─(system) plan_still_valid─▶ INTERVENTION_PROPOSED
    PLAN_INVALIDATED ─(system) recalculate_plan─▶ PLAN_RECALCULATED
    PLAN_RECALCULATED ─submit_evidence─▶ AWAITING_EVIDENCE_CONFIRMATION
    PLAN_RECALCULATED ─approve─▶ APPROVED
    APPROVED ─dispatch─▶ DISPATCHED
    DISPATCHED ─verify_source[VERIFIED]─▶ SOURCE_VERIFIED
    SOURCE_VERIFIED ─verify_destination[VERIFIED]─▶ DESTINATION_VERIFIED
    DESTINATION_VERIFIED ─verify_batch[VERIFIED]─▶ BATCH_MATCHED
    BATCH_MATCHED ─reconcile[coverage restored]─▶ COVERAGE_RESTORED
    COVERAGE_RESTORED ─care_delivery[all required obligations delivered]─▶ CARE_PROTECTED
    CARE_PROTECTED ─close─▶ CLOSED

A verification that is NOT_APPLIED / MISMATCH / UNKNOWN, or a reconcile that
still finds exposed events, is recorded and the state does not move. A case
with aggregate care obligations cannot reach CARE_PROTECTED until each
required delivery has a DELIVERED record. A case with no care obligations uses
the explicit event-row compatibility path: an empty post-reconcile exposure
set is sufficient because scheduled event rows are already the care evidence.
There is no action that asserts CARE_PROTECTED.
"""

from __future__ import annotations

from ..domain.enums import CaseAction, CaseState, SYSTEM_ACTIONS
from ..domain.errors import IllegalTransition

S, A = CaseState, CaseAction

TRANSITIONS: dict[tuple[CaseState, CaseAction], CaseState] = {
    (S.FORECASTED, A.PROPOSE): S.INTERVENTION_PROPOSED,
    (S.INTERVENTION_PROPOSED, A.SUBMIT_EVIDENCE): S.AWAITING_EVIDENCE_CONFIRMATION,
    (S.INTERVENTION_PROPOSED, A.APPROVE): S.APPROVED,
    (S.AWAITING_EVIDENCE_CONFIRMATION, A.CONFIRM_EVIDENCE): S.EVIDENCE_CONFIRMED,
    (S.AWAITING_EVIDENCE_CONFIRMATION, A.REJECT_EVIDENCE): S.INTERVENTION_PROPOSED,
    (S.EVIDENCE_CONFIRMED, A.INVALIDATE_PLAN): S.PLAN_INVALIDATED,
    (S.EVIDENCE_CONFIRMED, A.PLAN_STILL_VALID): S.INTERVENTION_PROPOSED,
    (S.PLAN_INVALIDATED, A.RECALCULATE_PLAN): S.PLAN_RECALCULATED,
    (S.PLAN_RECALCULATED, A.SUBMIT_EVIDENCE): S.AWAITING_EVIDENCE_CONFIRMATION,
    (S.PLAN_RECALCULATED, A.APPROVE): S.APPROVED,
    (S.APPROVED, A.DISPATCH): S.DISPATCHED,
    (S.DISPATCHED, A.VERIFY_SOURCE): S.SOURCE_VERIFIED,
    (S.SOURCE_VERIFIED, A.VERIFY_DESTINATION): S.DESTINATION_VERIFIED,
    (S.DESTINATION_VERIFIED, A.VERIFY_BATCH): S.BATCH_MATCHED,
    (S.BATCH_MATCHED, A.RECONCILE): S.COVERAGE_RESTORED,
    (S.COVERAGE_RESTORED, A.CARE_DELIVERY): S.CARE_PROTECTED,
    (S.CARE_PROTECTED, A.CLOSE): S.CLOSED,
}

# Actions that may legally be *attempted* in a state without moving it
# (a failed verification, a reconcile that finds exposure). Used for messages.
ATTEMPTABLE: dict[CaseState, frozenset[CaseAction]] = {
    S.DISPATCHED: frozenset({A.VERIFY_SOURCE}),
    S.SOURCE_VERIFIED: frozenset({A.VERIFY_DESTINATION}),
    S.DESTINATION_VERIFIED: frozenset({A.VERIFY_BATCH}),
    S.BATCH_MATCHED: frozenset({A.RECONCILE}),
    S.COVERAGE_RESTORED: frozenset({A.CARE_DELIVERY}),
}


def next_state(state: CaseState, action: CaseAction) -> CaseState:
    try:
        return TRANSITIONS[(state, action)]
    except KeyError:
        legal = sorted(a.value for (s, a) in TRANSITIONS if s == state)
        raise IllegalTransition(
            f"action '{action.value}' is not legal in state {state.value}; legal actions: {legal or 'none (terminal)'}",
            state=state.value, action=action.value, legal=legal,
        ) from None


def is_system_action(action: CaseAction) -> bool:
    return action in SYSTEM_ACTIONS


def legal_actions(state: CaseState, *, include_system: bool = False) -> list[CaseAction]:
    return [a for (s, a) in TRANSITIONS if s == state and (include_system or a not in SYSTEM_ACTIONS)]
