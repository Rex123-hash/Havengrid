import inspect
from datetime import timedelta

from havengrid.domain.enums import CandidateVerdict, RejectionReason
from havengrid.synthetic import sundargarh
from havengrid.kernel.interventions import allocate_fefo, explain
from tests.conftest import run_to_proposed


def by_donor(plan):
    return {c.donor_id: c for c in plan.candidates}


def test_sizing_is_72_rounded_to_80_pack(svc, case_id):
    run_to_proposed(svc)
    p = svc.current_plan(case_id)
    assert p.hold_through_day == 13
    assert p.required_quantity == 80
    assert all(c.quantity == 80 for c in p.candidates)


def test_ranking_is_lexicographic_and_chc_d_wins_on_expiry_relief(svc, case_id):
    run_to_proposed(svc)
    c = by_donor(svc.current_plan(case_id))
    assert c["chc-d"].verdict is CandidateVerdict.CHOSEN and c["chc-d"].rank == 1 and c["chc-d"].expiry_relief
    assert c["chc-b"].verdict is CandidateVerdict.HELD and c["chc-b"].rank == 2 and c["chc-b"].feasible
    assert c["warehouse"].verdict is CandidateVerdict.HELD and c["warehouse"].rank == 3 and c["warehouse"].feasible
    assert c["chc-b"].transit_hours < c["warehouse"].transit_hours  # rank 2 vs 3 decided by transit


def test_warehouse_arrives_before_breach_with_timestamps(svc, case_id, t0):
    run_to_proposed(svc)
    w = by_donor(svc.current_plan(case_id))["warehouse"]
    assert w.dispatch_ready_at == t0 + timedelta(hours=24)
    assert w.expected_arrival_at == t0 + timedelta(hours=168)
    assert w.arrival_day == 8
    assert w.expected_arrival_at < w.recipient_breach_at
    assert RejectionReason.ARRIVES_AFTER_RECIPIENT_BREACH not in w.rejection_reasons


def test_kansbahal_rejected_primarily_for_donor_safety(svc, case_id):
    run_to_proposed(svc)
    k = by_donor(svc.current_plan(case_id))["kansbahal"]
    assert not k.feasible
    assert k.rejection_reasons == (RejectionReason.DONOR_ALREADY_AT_RISK,)
    assert k.donor_coverage_breach_day == 7 and k.donor_protection_window_days == 10


def test_lahunipada_rejected_for_insufficient_transferable_stock(svc, case_id):
    run_to_proposed(svc)
    lahu = by_donor(svc.current_plan(case_id))["lahunipada"]
    assert lahu.rejection_reasons == (RejectionReason.INSUFFICIENT_TRANSFERABLE_STOCK,)
    assert lahu.transferable == 20 and lahu.quantity == 80


def test_no_duplicate_reasons_anywhere(svc, case_id):
    run_to_proposed(svc)
    for c in svc.current_plan(case_id).candidates:
        assert len(c.rejection_reasons) == len(set(c.rejection_reasons))


def test_donor_safety_is_a_forward_projection_not_point_in_time(svc, case_id):
    run_to_proposed(svc)
    d = by_donor(svc.current_plan(case_id))["chc-d"]
    assert d.transferable == 136  # min over the 14-day window of (closing - cover)
    assert d.donor_post_transfer_breach_day is None
    assert d.donor_post_transfer_margin == 56


def test_only_routed_facilities_are_candidates(svc, case_id):
    run_to_proposed(svc)
    assert set(by_donor(svc.current_plan(case_id))) == {"chc-d", "chc-b", "warehouse", "kansbahal", "lahunipada"}


def test_fefo_allocation_consumes_earliest_expiry_first(svc, item_id):
    batches = svc.repo.batches_for("chc-d", item_id)
    assert [(a.batch_id, a.quantity) for a in allocate_fefo(batches, 80)] == [("AMX-2401-K", 80)]
    assert [(a.batch_id, a.quantity) for a in allocate_fefo(batches, 120)] == [("AMX-2401-K", 90), ("AMX-2402-M", 30)]


def test_explanations_are_generated_from_codes():
    for r in RejectionReason:
        assert explain(r)


def test_verdict_is_output_only(svc, case_id):
    run_to_proposed(svc)
    assert svc.current_plan(case_id).chosen.donor_id == "chc-d"
    from tests.test_fixture import _code_only
    src = _code_only(sundargarh)
    assert "chc-d" in src and "chosen" not in src
