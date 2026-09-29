"""The Sundargarh story, end to end. Every assertion is a derived value.

No number below is read from the fixture as a stored outcome; each emerges
from the kernel applied to facts and policies.
"""

from decimal import Decimal

from havengrid.domain.enums import CandidateVerdict, CareCategory, CaseState, EvidenceState, ReconciliationOutcome, RejectionReason, VerificationOutcome


def test_sundargarh_story_end_to_end(svc, case_id, item_id):
    repo = svc.repo

    # ── load ──────────────────────────────────────────────────────────────
    assert repo.canonical_inventory("bhatpar", item_id).quantity == 143
    bhatpar = svc.forecast("bhatpar", item_id)
    assert sum(r.demand for r in bhatpar.projection if r.day <= 14) == 191
    assert 191 - 143 == 48
    assert len(repo.care_events_for("bhatpar", item_id)) == 23

    # ── forecast ──────────────────────────────────────────────────────────
    assert bhatpar.coverage_breach_day == 8
    assert bhatpar.stockout_day == 11

    # ── care blast radius ─────────────────────────────────────────────────
    impact = svc.care_impact("bhatpar", item_id)
    assert impact.exposed_total == 13
    assert impact.exposed_by_category[CareCategory.PAEDIATRIC] == 7
    assert impact.exposed_by_category[CareCategory.MATERNAL] == 4
    assert impact.exposed_by_category[CareCategory.SCHEDULED] == 2
    assert impact.unserved_total == 6
    originally_exposed = set(impact.exposed_event_ids)

    # ── evaluate interventions ────────────────────────────────────────────
    case = svc.propose(case_id)
    plan = svc.current_plan(case_id)
    cands = {c.donor_id: c for c in plan.candidates}
    assert plan.chosen.quantity == 80
    assert plan.chosen.donor_id == "chc-d" and cands["chc-d"].rank == 1
    assert cands["chc-b"].feasible and cands["chc-b"].verdict is CandidateVerdict.HELD and cands["chc-b"].rank == 2
    assert cands["warehouse"].feasible and cands["warehouse"].verdict is CandidateVerdict.HELD and cands["warehouse"].rank == 3
    assert cands["kansbahal"].rejection_reasons == (RejectionReason.DONOR_ALREADY_AT_RISK,)
    assert cands["lahunipada"].rejection_reasons == (RejectionReason.INSUFFICIENT_TRANSFERABLE_STOCK,)
    assert set(case.originally_exposed_ids) == originally_exposed

    # ── Reality Lens: evidence submitted, nothing changes ────────────────
    case, ev = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126, confidence=Decimal("0.83"),
                                   captured_via="field photograph · ward stock register")
    assert ev.state is EvidenceState.AWAITING_CONFIRMATION
    assert repo.canonical_inventory("chc-d", item_id).quantity == 286
    assert svc.current_plan(case_id).id == plan.id and svc.current_plan(case_id).chosen.donor_id == "chc-d"

    # ── confirm ───────────────────────────────────────────────────────────
    case = svc.confirm_evidence(case_id, ev.id, confirmed_by="district-pharmacist")
    assert repo.canonical_inventory("chc-d", item_id).quantity == 126
    lineage = repo.inventory_lineage("chc-d", item_id)
    assert [(r.quantity, r.canonical) for r in lineage] == [(286, False), (126, True)]
    assert svc.forecast("chc-d", item_id).coverage_breach_day == 12
    assert repo.plan(plan.id).invalidated and repo.plan(plan.id).invalidation_reason is RejectionReason.INVALIDATED_BY_CONFIRMED_EVIDENCE

    # ── re-evaluate ───────────────────────────────────────────────────────
    assert case.state is CaseState.PLAN_RECALCULATED
    plan2 = svc.current_plan(case_id)
    cands2 = {c.donor_id: c for c in plan2.candidates}
    assert not cands2["chc-d"].feasible
    assert plan2.chosen.donor_id == "chc-b" and plan2.chosen.quantity == 80

    # ── recovery ──────────────────────────────────────────────────────────
    svc.approve(case_id, approved_by="district-medical-officer")
    case = svc.dispatch(case_id, dispatched_by="chc-b-pharmacist")
    assert case.state is CaseState.DISPATCHED

    case, v = svc.verify_source(case_id, observed_quantity=260, verified_by="chc-b-pharmacist")
    assert v.outcome is VerificationOutcome.VERIFIED and case.state is CaseState.SOURCE_VERIFIED
    case, v = svc.verify_destination(case_id, observed_quantity=223, verified_by="bhatpar-pharmacist")
    assert v.outcome is VerificationOutcome.VERIFIED and case.state is CaseState.DESTINATION_VERIFIED
    case, v = svc.verify_batch(case_id, observed_batch_ids=["AMX-2403-B"], observed_quantity=80, verified_by="bhatpar-pharmacist")
    assert v.outcome is VerificationOutcome.VERIFIED and case.state is CaseState.BATCH_MATCHED

    # ── reconcile: computed, not asserted ─────────────────────────────────
    case, rec = svc.reconcile(case_id)
    assert rec.outcome is ReconciliationOutcome.CARE_PROTECTED
    assert rec.still_exposed_ids == ()
    assert rec.protected_count == 13
    assert set(rec.originally_exposed_ids) == originally_exposed
    assert case.state is CaseState.CARE_PROTECTED
    assert svc.care_impact("bhatpar", item_id).exposed_total == 0
    assert svc.forecast("bhatpar", item_id).coverage_breach_day is None   # nothing else in the 30-day horizon

    # ── close ─────────────────────────────────────────────────────────────
    case = svc.close(case_id, closed_by="district-medical-officer")
    assert case.state is CaseState.CLOSED and case.care_protected_count == 13

    # ── reset ─────────────────────────────────────────────────────────────
    svc.reset()
    assert repo.case(case_id).state is CaseState.FORECASTED
    assert repo.canonical_inventory("chc-d", item_id).quantity == 286
    assert repo.canonical_inventory("bhatpar", item_id).quantity == 143
    assert len(repo.inventory_lineage("chc-d", item_id)) == 1
    assert repo.audit_for() == []
    assert svc.now() == repo.state().district.forecast_at
    assert svc.forecast("bhatpar", item_id).coverage_breach_day == 8
    assert svc.care_impact("bhatpar", item_id).exposed_total == 13
