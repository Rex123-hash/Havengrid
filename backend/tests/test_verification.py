from havengrid.domain.enums import CaseState, ReconciliationOutcome, VerificationOutcome
from havengrid.kernel.verification import classify_batch, classify_quantity
from tests.conftest import run_to_batch_matched, run_to_recalculated


def test_quantity_classification_is_four_valued():
    assert classify_quantity(observed=None, expected=260, before=340) is VerificationOutcome.UNKNOWN
    assert classify_quantity(observed=260, expected=260, before=340) is VerificationOutcome.VERIFIED
    assert classify_quantity(observed=340, expected=260, before=340) is VerificationOutcome.NOT_APPLIED
    assert classify_quantity(observed=300, expected=260, before=340) is VerificationOutcome.MISMATCH


def test_batch_classification():
    assert classify_batch(observed_batch_ids=None, observed_quantity=None, expected_batch_ids=["B"], expected_quantity=80) is VerificationOutcome.UNKNOWN
    assert classify_batch(observed_batch_ids=[], observed_quantity=0, expected_batch_ids=["B"], expected_quantity=80) is VerificationOutcome.NOT_APPLIED
    assert classify_batch(observed_batch_ids=["B"], observed_quantity=80, expected_batch_ids=["B"], expected_quantity=80) is VerificationOutcome.VERIFIED
    assert classify_batch(observed_batch_ids=["B"], observed_quantity=70, expected_batch_ids=["B"], expected_quantity=80) is VerificationOutcome.MISMATCH


def _to_dispatched(svc, case_id):
    run_to_recalculated(svc)
    svc.approve(case_id, approved_by="dmo")
    return svc.dispatch(case_id, dispatched_by="chc-b")


def test_expected_values_come_from_canonical_at_verification_time(svc, case_id):
    _to_dispatched(svc, case_id)
    case, v = svc.verify_source(case_id, observed_quantity=260, verified_by="chc-b")
    assert v.expected == "260" and v.outcome is VerificationOutcome.VERIFIED and "inv-chc-b-001 = 340" in v.note
    case, v = svc.verify_destination(case_id, observed_quantity=223, verified_by="bhatpar")
    assert v.expected == "223" and case.state is CaseState.DESTINATION_VERIFIED


def test_unknown_never_advances(svc, case_id):
    _to_dispatched(svc, case_id)
    case, v = svc.verify_source(case_id, observed_quantity=None, verified_by="chc-b")
    assert v.outcome is VerificationOutcome.UNKNOWN and case.state is CaseState.DISPATCHED
    assert any(a.action == "verify_source:unknown" for a in svc.repo.audit_for(case_id))


def test_not_applied_and_mismatch_never_advance_but_are_recorded(svc, case_id):
    _to_dispatched(svc, case_id)
    case, v = svc.verify_source(case_id, observed_quantity=340, verified_by="chc-b")
    assert v.outcome is VerificationOutcome.NOT_APPLIED and case.state is CaseState.DISPATCHED
    case, v = svc.verify_source(case_id, observed_quantity=300, verified_by="chc-b")
    assert v.outcome is VerificationOutcome.MISMATCH and case.state is CaseState.DISPATCHED
    # a correct count afterwards still advances
    case, v = svc.verify_source(case_id, observed_quantity=260, verified_by="chc-b")
    assert v.outcome is VerificationOutcome.VERIFIED and case.state is CaseState.SOURCE_VERIFIED
    assert len(case.verification_ids) == 3


def test_reconcile_commits_verified_counts_with_lineage_and_no_double_credit(svc, case_id, item_id):
    run_to_batch_matched(svc)
    case, rec = svc.reconcile(case_id)
    assert rec.outcome is ReconciliationOutcome.CARE_PROTECTED and case.state is CaseState.CARE_PROTECTED
    b = svc.repo.inventory_lineage("bhatpar", item_id)
    assert [(r.quantity, r.canonical) for r in b] == [(143, False), (223, True)]
    xfer = svc.repo.state().supplies[case.transfer_supply_id]
    assert xfer.state.value == "received"
    a = svc.forecast("bhatpar", item_id)
    assert a.projection[0].opening == 223 and a.projection[0].credit == 0     # transfer not credited again
    assert next(r for r in a.projection if r.day == 14).credit == 200         # scheduled replenishment still future
    assert a.coverage_breach_day is None


def test_reconcile_not_ready_without_all_verifications(svc, case_id):
    _to_dispatched(svc, case_id)
    svc.verify_source(case_id, observed_quantity=260, verified_by="chc-b")
    import pytest
    from havengrid.domain.errors import IllegalTransition
    with pytest.raises(IllegalTransition):
        svc.reconcile(case_id)   # not in BATCH_MATCHED


def test_reconcile_is_idempotent(svc, case_id):
    run_to_batch_matched(svc)
    a, ra = svc.reconcile(case_id, command_id="rec-1")
    b, rb = svc.reconcile(case_id, command_id="rec-1")
    assert a.state is b.state is CaseState.CARE_PROTECTED and ra.id == rb.id


def test_close_requires_care_protected(svc, case_id):
    run_to_batch_matched(svc)
    import pytest
    from havengrid.domain.errors import IllegalTransition
    with pytest.raises(IllegalTransition):
        svc.close(case_id, closed_by="dmo")
    svc.reconcile(case_id)
    assert svc.close(case_id, closed_by="dmo").state is CaseState.CLOSED
