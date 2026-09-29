"""Safety regressions for unavailable inputs and rejected commands."""

from copy import deepcopy
from decimal import Decimal

import pytest

from havengrid.domain.enums import CaseState, ForecastStatus
from havengrid.domain.errors import IllegalTransition, InvariantViolation, NotFound
from havengrid.kernel.interventions import evaluate_candidates
from havengrid.rehearsal.sundargarh import CASE_ID, ITEM_ID, RECIPIENT_ID, build_sundargarh_rehearsal
from havengrid.service import HavenGridService
from havengrid.store import InMemoryRepository
from tests.conftest import run_to_batch_matched


def unchanged_after_error(service, operation, error):
    before = deepcopy(service.repo.state())
    tick = service._tick
    with pytest.raises(error):
        operation()
    assert service.repo.state() == before
    assert service._tick == tick


def test_ifa_unknown_then_confirmed_observation_restores_planning():
    service = HavenGridService(InMemoryRepository(build_sundargarh_rehearsal))
    assert service.repo.canonical_inventory(RECIPIENT_ID, ITEM_ID) is None
    assert service.forecast(RECIPIENT_ID, ITEM_ID).status is ForecastStatus.UNAVAILABLE
    impact = service.care_impact(RECIPIENT_ID, ITEM_ID)
    assert impact.status is ForecastStatus.UNAVAILABLE
    assert impact.exposed_total is None and impact.unserved_total is None

    unchanged_after_error(service, lambda: evaluate_candidates(
        service.repo, recipient_id=RECIPIENT_ID, item_id=ITEM_ID,
        plan_id="probe", case_id=CASE_ID, evaluated_at=service.now()), InvariantViolation)
    unchanged_after_error(service, lambda: service.propose(CASE_ID), InvariantViolation)
    assert service.repo.case(CASE_ID).plan_id is None
    assert not service.repo.state().plans
    assert not any(s.id.startswith("xfer-") for s in service.repo.state().supplies.values())

    _, evidence = service.submit_evidence(CASE_ID, facility_id=RECIPIENT_ID,
                                           observed_quantity=30, confidence=Decimal("0.95"),
                                           captured_via="controlled rehearsal shelf count",
                                           evidence_class="REHEARSAL_FIELD_OBSERVATION")
    service.confirm_evidence(CASE_ID, evidence.id, confirmed_by="rehearsal-pharmacist")
    assert service.forecast(RECIPIENT_ID, ITEM_ID).status is ForecastStatus.FORECAST
    assert service.care_impact(RECIPIENT_ID, ITEM_ID).exposed_total == 13
    assert service.propose(CASE_ID).state is CaseState.INTERVENTION_PROPOSED
    chosen = service.current_plan(CASE_ID).chosen
    assert chosen is not None and chosen.donor_id == "sdh-bonai" and chosen.quantity == 47


def test_api_keeps_unknown_impact_distinct_from_known_zero(client):
    unavailable = client.get("/api/facilities/kutra/care-impact").json()
    zero = client.get("/api/facilities/remed/care-impact").json()
    assert unavailable["status"] == "unavailable" and unavailable["exposed_total"] is None
    assert unavailable["unserved_total"] is None and unavailable["exposed_by_category"] is None
    assert zero["status"] == "forecast" and zero["exposed_total"] == 0


def test_dispatch_before_approval_is_side_effect_free(svc, case_id):
    svc.propose(case_id)
    unchanged_after_error(svc, lambda: svc.dispatch(case_id, dispatched_by="tester"), IllegalTransition)
    assert svc.repo.case(case_id).state is CaseState.INTERVENTION_PROPOSED
    assert svc.repo.case(case_id).transfer_supply_id is None
    assert not any(a.action == "dispatch" for a in svc.repo.state().audit)


def test_other_rejected_commands_do_not_mutate(svc, case_id):
    unchanged_after_error(svc, lambda: svc.approve(case_id, approved_by="tester"), InvariantViolation)
    unchanged_after_error(svc, lambda: svc.verify_source(case_id, observed_quantity=1, verified_by="tester"), IllegalTransition)
    unchanged_after_error(svc, lambda: svc.verify_destination(case_id, observed_quantity=1, verified_by="tester"), IllegalTransition)
    unchanged_after_error(svc, lambda: svc.verify_batch(case_id, observed_batch_ids=[], observed_quantity=1, verified_by="tester"), IllegalTransition)
    unchanged_after_error(svc, lambda: svc.reconcile(case_id), IllegalTransition)
    unchanged_after_error(svc, lambda: svc.close(case_id, closed_by="tester"), IllegalTransition)
    unchanged_after_error(svc, lambda: svc.submit_evidence(case_id, facility_id="chc-d",
                          observed_quantity=-1, confidence=Decimal("0.83"), captured_via="field register"), InvariantViolation)
    svc.propose(case_id)
    unchanged_after_error(svc, lambda: svc.propose(case_id), IllegalTransition)
    _, evidence = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126,
                                      confidence=Decimal("0.83"), captured_via="field register")
    unchanged_after_error(svc, lambda: svc.submit_evidence(case_id, facility_id="chc-d",
                          observed_quantity=125, confidence=Decimal("0.83"), captured_via="field register"), IllegalTransition)
    svc.reject_evidence(case_id, evidence.id, rejected_by="tester")
    unchanged_after_error(svc, lambda: svc.confirm_evidence(case_id, evidence.id,
                          confirmed_by="tester"), IllegalTransition)


def test_reconcile_rejects_newly_unavailable_inputs_without_committing_counts(svc, case_id, item_id):
    run_to_batch_matched(svc)
    svc.repo.state().demand.pop(("bhatpar", item_id))
    unchanged_after_error(svc, lambda: svc.reconcile(case_id), InvariantViolation)


def test_missing_recipient_demand_cannot_create_a_plan(svc, case_id, item_id):
    svc.repo.state().demand.pop(("bhatpar", item_id))
    unchanged_after_error(svc, lambda: svc.propose(case_id), InvariantViolation)
    assert not svc.repo.state().plans


@pytest.mark.parametrize("decision", ["confirm", "reject"])
def test_evidence_decisions_require_case_ownership(svc, case_id, decision):
    svc.propose(case_id)
    _, evidence = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126,
                                      confidence=Decimal("0.83"), captured_via="field register")
    other_id = "case-other"
    svc.repo.put_case(svc.repo.case(case_id).model_copy(update={"id": other_id}))
    if decision == "confirm":
        operation = lambda: svc.confirm_evidence(other_id, evidence.id, confirmed_by="tester")
    else:
        operation = lambda: svc.reject_evidence(other_id, evidence.id, rejected_by="tester")
    unchanged_after_error(svc, operation, NotFound)
    assert svc.repo.evidence(evidence.id).state.value == "awaiting_confirmation"
