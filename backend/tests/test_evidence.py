from decimal import Decimal

import pytest

from havengrid.domain.enums import CaseState, EvidenceState, ProvenanceStatus, RejectionReason
from havengrid.domain.errors import IllegalTransition
from tests.conftest import run_to_proposed, run_to_recalculated


def test_unconfirmed_evidence_does_not_touch_canonical_or_plan(svc, case_id, item_id, d083):
    run_to_proposed(svc)
    plan_before = svc.current_plan(case_id)
    case, ev = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126, confidence=d083, captured_via="photo")
    assert case.state is CaseState.AWAITING_EVIDENCE_CONFIRMATION
    assert ev.state is EvidenceState.AWAITING_CONFIRMATION
    assert svc.repo.canonical_inventory("chc-d", item_id).quantity == 286
    assert svc.current_plan(case_id).id == plan_before.id
    assert svc.current_plan(case_id).chosen.donor_id == "chc-d"
    assert not svc.current_plan(case_id).invalidated
    assert ev.canonical_quantity_at_submission == 286


def test_confirmation_creates_lineage_not_overwrite(svc, case_id, item_id):
    case, ev = run_to_recalculated(svc)
    lineage = svc.repo.inventory_lineage("chc-d", item_id)
    assert [(r.quantity, r.canonical) for r in lineage] == [(286, False), (126, True)]
    old, new = lineage
    assert old.superseded_by_id == new.id and new.supersedes_id == old.id
    assert new.evidence_id == ev.id and new.provenance.status is ProvenanceStatus.VERIFIED
    assert new.provenance.confidence == Decimal("0.83")
    ev_after = svc.repo.evidence(ev.id)
    assert ev_after.state is EvidenceState.CONFIRMED
    assert ev_after.committed_record_id == new.id and ev_after.decided_by == "district-pharmacist"


def test_confirmation_cascades_to_chc_d_own_risk_and_replans(svc, case_id, item_id):
    case, _ = run_to_recalculated(svc)
    assert case.state is CaseState.PLAN_RECALCULATED
    assert svc.forecast("chc-d", item_id).coverage_breach_day == 12
    assert svc.care_impact("chc-d", item_id).exposed_total == 2
    old = svc.repo.plan(case.previous_plan_ids[0])
    assert old.invalidated and old.invalidation_reason is RejectionReason.INVALIDATED_BY_CONFIRMED_EVIDENCE
    assert old.superseded_by_id == case.plan_id
    new = svc.current_plan(case_id)
    assert new.chosen.donor_id == "chc-b" and new.chosen.quantity == 80
    d = {c.donor_id: c for c in new.candidates}["chc-d"]
    assert not d.feasible and d.rejection_reasons == (RejectionReason.DONOR_ALREADY_AT_RISK,)


def test_audit_records_the_causal_chain(svc, case_id):
    run_to_recalculated(svc)
    actions = [a.action for a in svc.repo.audit_for(case_id)]
    assert actions == ["propose", "submit_evidence", "confirm_evidence", "invalidate_plan", "recalculate_plan"]


def test_rejection_leaves_everything_intact(svc, case_id, item_id, d083):
    run_to_proposed(svc)
    _, ev = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126, confidence=d083, captured_via="photo")
    case = svc.reject_evidence(case_id, ev.id, rejected_by="pharmacist", note="photo illegible")
    assert case.state is CaseState.INTERVENTION_PROPOSED
    assert svc.repo.canonical_inventory("chc-d", item_id).quantity == 286
    assert svc.repo.evidence(ev.id).state is EvidenceState.REJECTED
    assert svc.current_plan(case_id).chosen.donor_id == "chc-d"


def test_cannot_confirm_twice(svc, case_id):
    _, ev = run_to_recalculated(svc)
    with pytest.raises(IllegalTransition):
        svc.confirm_evidence(case_id, ev.id, confirmed_by="x")


def test_evidence_that_does_not_change_plan_keeps_it(svc, case_id, item_id, d083):
    run_to_proposed(svc)
    _, ev = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=280, confidence=d083, captured_via="photo")
    case = svc.confirm_evidence(case_id, ev.id, confirmed_by="pharmacist")
    assert case.state is CaseState.INTERVENTION_PROPOSED
    assert svc.repo.canonical_inventory("chc-d", item_id).quantity == 280
    assert svc.current_plan(case_id).chosen.donor_id == "chc-d" and not case.previous_plan_ids
