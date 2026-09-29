"""Application service: the only place state changes.

Owns: the synthetic clock, command idempotency, audit, evidence lineage, plan
invalidation/replanning, verification and reconciliation. The kernel modules
are pure; this module sequences them.

Synthetic clock: every command advances 30 minutes from T0. The whole recovery
workflow therefore completes inside bucket 1, before any demand settles, which
is what makes "canonical ± q" a legitimate expectation for verification.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .domain.enums import (
    CaseAction,
    CaseState,
    EvidenceState,
    IncomingSupplyState,
    Origin,
    ProvenanceStatus,
    ReconciliationOutcome,
    RejectionReason,
    SourceType,
    VerificationKind,
    VerificationOutcome,
    ExposureKind,
    CareDeliveryOutcome,
    CoverageRecoveryStatus,
)
from .domain.errors import IllegalTransition, InvariantViolation, NotFound
from .commands import CommandAuthorizer, TemporaryCommandAuthorizer
from .settings import HavenGridMode
from .domain.models import (
    AuditEvent,
    CareImpact,
    CoverageAssessment,
    EvidenceRecord,
    IncomingSupply,
    InterventionPlan,
    InventoryRecord,
    Provenance,
    ReconciliationRecord,
    RecoveryCase,
    VerificationRecord,
    ExposureRef,
    CareDeliveryRecord,
)
from .synthetic.sundargarh import build_sundargarh
from .kernel.care_impact import compute_care_impact
from .kernel.interventions import evaluate_candidates, forecast_for
from .kernel.state_machine import is_system_action, next_state
from .kernel.verification import classify_batch, classify_quantity
from .store import InMemoryRepository

CLOCK_STEP = timedelta(minutes=30)


class HavenGridService:
    def __init__(self, repo: InMemoryRepository | None = None, *, actor_origin: Origin = Origin.SYNTHETIC_TEST,
                 mode: HavenGridMode = HavenGridMode.REHEARSAL,
                 command_authorizer: CommandAuthorizer | None = None) -> None:
        self.repo = repo or InMemoryRepository(build_sundargarh)
        state = self.repo.state()
        self._initial_tick = max(0, (state.audit[-1].at - state.district.forecast_at) // CLOCK_STEP) if state.audit else 0
        self._tick = self._initial_tick
        # Origin stamped on records created from human actions in this deployment.
        # SYNTHETIC_TEST on the synthetic source; USER_SUPPLIED_EVIDENCE on a real one.
        self.actor_origin = actor_origin
        self.mode = mode
        self.command_authorizer = command_authorizer or TemporaryCommandAuthorizer()

    # ── clock / reset ─────────────────────────────────────────────────────

    def now(self) -> datetime:
        return self.repo.state().district.forecast_at + CLOCK_STEP * self._tick

    def _advance_clock(self) -> datetime:
        self._tick += 1
        return self.now()

    def reset(self) -> None:
        if self.mode is HavenGridMode.OPERATIONAL:
            raise IllegalTransition("reset is rehearsal-only and does not exist in operational mode")
        self.repo.reset()
        self._tick = self._initial_tick

    def authorize_command(self, *, action: CaseAction, actor: str, capability: str | None) -> None:
        """Authorize one explicit command; reads and internal system actions never call this."""
        if self.mode is HavenGridMode.OPERATIONAL:
            self.command_authorizer.authorize(action=action, actor=actor, capability=capability)

    # ── reads ─────────────────────────────────────────────────────────────

    def forecast(self, facility_id: str, item_id: str) -> CoverageAssessment:
        self.repo.facility(facility_id)
        return forecast_for(self.repo, facility_id, item_id)

    def care_impact(self, facility_id: str, item_id: str) -> CareImpact:
        a = self.forecast(facility_id, item_id)
        return compute_care_impact(self.repo.state().district, a, self.repo.care_events_for(facility_id, item_id), self.repo.care_obligations_for(facility_id, item_id))

    def data_origins(self) -> list[str]:
        """Distinct origins of every FACT record currently held (not kernel outputs)."""
        st = self.repo.state()
        provs = [r.provenance for r in st.inventory.values()] + [r.provenance for r in st.supplies.values()] + \
                [r.provenance for r in st.care_events.values()] + [r.provenance for r in st.care_obligations.values()] + \
                [r.provenance for r in st.batches.values()] + [r.provenance for r in st.routes.values()] + \
                [r.provenance for r in st.route_observations.values()] + [r.provenance for r in st.demand.values()] + \
                [r.provenance for r in st.district_stock_signals.values()] + [r.provenance for r in st.programme_activity.values()] + [st.district.policy.provenance]
        return sorted({p.origin.value for p in provs})

    def network_forecast(self, item_id: str) -> dict[str, CoverageAssessment]:
        return {f.id: forecast_for(self.repo, f.id, item_id) for f in self.repo.all_facilities()}

    def network_care_impact(self, item_id: str) -> dict[str, CareImpact]:
        d = self.repo.state().district
        return {fid: compute_care_impact(d, a, self.repo.care_events_for(fid, item_id), self.repo.care_obligations_for(fid, item_id)) for fid, a in self.network_forecast(item_id).items()}

    def current_plan(self, case_id: str) -> InterventionPlan | None:
        c = self.repo.case(case_id)
        return self.repo.plan(c.plan_id) if c.plan_id else None

    # ── internals ─────────────────────────────────────────────────────────

    def _audit(self, case: RecoveryCase | None, action: str, from_state: CaseState | None, to_state: CaseState | None, **detail: object) -> None:
        st = self.repo.state()
        self.repo.append_audit(AuditEvent(seq=len(st.audit) + 1, at=self.now(), case_id=case.id if case else None,
                                          action=action, from_state=from_state, to_state=to_state, detail=detail))

    def _transition(self, case: RecoveryCase, action: CaseAction, **detail: object) -> RecoveryCase:
        new = next_state(case.state, action)
        updated = case.model_copy(update={"state": new})
        self.repo.put_case(updated)
        self._audit(updated, action.value, case.state, new, **detail)
        return updated

    def _idempotent(self, case: RecoveryCase, command_id: str | None) -> RecoveryCase | None:
        if command_id and command_id in case.applied_command_ids:
            return case
        return None

    def _mark_applied(self, case: RecoveryCase, command_id: str | None) -> RecoveryCase:
        if not command_id:
            return case
        updated = case.model_copy(update={"applied_command_ids": (*case.applied_command_ids, command_id)})
        self.repo.put_case(updated)
        return updated

    def _evaluate(self, case: RecoveryCase, *, evaluated_at: datetime | None = None) -> InterventionPlan:
        # Evaluation can reject unavailable inputs; do not consume an ID first.
        plan_id = f"plan-{self.repo.state().counters.get('plan', 0) + 1:03d}"
        plan = evaluate_candidates(self.repo, recipient_id=case.recipient_id, item_id=case.item_id, plan_id=plan_id, case_id=case.id, evaluated_at=evaluated_at or self.now())
        self.repo.next_id("plan")
        self.repo.put_plan(plan)
        return plan

    # ── commands ──────────────────────────────────────────────────────────

    def propose(self, case_id: str, *, command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        next_state(case.state, CaseAction.PROPOSE)
        impact = self.care_impact(case.recipient_id, case.item_id)
        if impact.status.value == "unavailable":
            raise InvariantViolation("cannot propose intervention: recipient care impact is unavailable")
        plan = self._evaluate(case, evaluated_at=self.now() + CLOCK_STEP)
        self._advance_clock()
        refs = tuple([ExposureRef(kind=ExposureKind.CARE_EVENT, id=i) for i in impact.exposed_event_ids] +
                     [ExposureRef(kind=ExposureKind.CARE_OBLIGATION, id=i) for i in impact.exposed_obligation_ids])
        case = case.model_copy(update={"plan_id": plan.id, "originally_exposed_ids": impact.exposed_event_ids, "originally_exposed_refs": refs})
        self.repo.put_case(case)
        case = self._transition(case, CaseAction.PROPOSE, plan_id=plan.id, chosen=plan.chosen.donor_id if plan.chosen else None,
                                quantity=plan.chosen.quantity if plan.chosen else None, exposed=impact.exposed_total)
        return self._mark_applied(case, command_id)

    def submit_evidence(self, case_id: str, *, facility_id: str, observed_quantity: int, confidence: Decimal, captured_via: str,
                        source_type: SourceType = SourceType.FIELD_REGISTER, evidence_class: str = "USER_SUPPLIED_EVIDENCE",
                        command_id: str | None = None) -> tuple[RecoveryCase, EvidenceRecord]:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            ev = self.repo.evidence(done.evidence_ids[-1])
            return done, ev
        self.repo.facility(facility_id)
        if observed_quantity < 0 or not Decimal(0) <= confidence <= Decimal(1):
            raise InvariantViolation("evidence quantity must be nonnegative and confidence must be within [0, 1]")
        canonical = self.repo.canonical_inventory(facility_id, case.item_id)
        if not (case.state is CaseState.FORECASTED and canonical is None):
            next_state(case.state, CaseAction.SUBMIT_EVIDENCE)
        at = self._advance_clock()
        ev = EvidenceRecord(
            id=self.repo.next_id("ev"), case_id=case.id, facility_id=facility_id, item_id=case.item_id,
            observed_quantity=observed_quantity, confidence=confidence, source_type=source_type, captured_via=captured_via,
            observed_at=at, state=EvidenceState.AWAITING_CONFIRMATION,
            canonical_quantity_at_submission=canonical.quantity if canonical else None,
            canonical_record_id_at_submission=canonical.id if canonical else None,
            evidence_class=evidence_class,
        )
        self.repo.put_evidence(ev)
        # THE RULE: canonical is untouched; the plan is untouched. Only the case state moves.
        case = case.model_copy(update={"evidence_ids": (*case.evidence_ids, ev.id)})
        self.repo.put_case(case)
        if case.state is CaseState.FORECASTED and canonical is None:
            # Initial inventory is a first observation, not a contradiction of
            # an existing plan.  Keep the case FORECASTED so the normal propose
            # command remains the next legal lifecycle action.
            self._audit(case, CaseAction.SUBMIT_EVIDENCE.value, case.state, case.state,
                        evidence_id=ev.id, observed=observed_quantity, canonical_unchanged=None,
                        plan_unchanged=case.plan_id, evidence_class=evidence_class)
        else:
            case = self._transition(case, CaseAction.SUBMIT_EVIDENCE, evidence_id=ev.id, observed=observed_quantity,
                                    canonical_unchanged=canonical.quantity if canonical else None, plan_unchanged=case.plan_id,
                                    evidence_class=evidence_class)
        return self._mark_applied(case, command_id), ev

    def confirm_evidence(self, case_id: str, evidence_id: str, *, confirmed_by: str, note: str = "", command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        ev = self.repo.evidence(evidence_id)
        if ev.case_id != case.id:
            raise NotFound(f"evidence '{evidence_id}' does not belong to case '{case_id}'")
        if ev.state != EvidenceState.AWAITING_CONFIRMATION:
            raise IllegalTransition(f"evidence '{evidence_id}' is {ev.state.value}, not awaiting confirmation")
        old = self.repo.canonical_inventory(ev.facility_id, ev.item_id)
        if not (case.state is CaseState.FORECASTED and old is None):
            next_state(case.state, CaseAction.CONFIRM_EVIDENCE)
        at = self._advance_clock()

        # 1. commit a NEW canonical record with lineage; retire the old one (never overwrite)
        new = InventoryRecord(
            id=self.repo.next_id(f"inv-{ev.facility_id}-v"), facility_id=ev.facility_id, item_id=ev.item_id, quantity=ev.observed_quantity,
            canonical=True, supersedes_id=old.id if old else None, evidence_id=ev.id,
            provenance=Provenance(source_type=ev.source_type, status=ProvenanceStatus.VERIFIED, observed_at=at,
                                  source_ref=f"evidence/{ev.id}", origin=self.actor_origin, confidence=ev.confidence,
                                  note=(f"confirmed by {confirmed_by}; supersedes {old.id} ({old.quantity})" if old else
                                        f"confirmed by {confirmed_by}; initial field observation; no prior facility inventory")),
        )
        if old is not None:
            self.repo.put_inventory(old.model_copy(update={"canonical": False, "superseded_by_id": new.id}))
        self.repo.put_inventory(new)
        self.repo.put_evidence(ev.model_copy(update={"state": EvidenceState.CONFIRMED, "committed_record_id": new.id, "decided_at": at, "decided_by": confirmed_by, "decision_note": note}))
        if case.state is CaseState.FORECASTED and old is None:
            self._audit(case, CaseAction.CONFIRM_EVIDENCE.value, case.state, case.state, evidence_id=ev.id,
                        old_record=None, old_quantity=None, new_record=new.id, new_quantity=new.quantity,
                        confirmed_by=confirmed_by, evidence_class=ev.evidence_class)
        else:
            case = self._transition(case, CaseAction.CONFIRM_EVIDENCE, evidence_id=ev.id,
                                    old_record=old.id if old else None, old_quantity=old.quantity if old else None,
                                    new_record=new.id, new_quantity=new.quantity, confirmed_by=confirmed_by)

        if case.state is CaseState.FORECASTED and old is None:
            return self._mark_applied(case, command_id)

        # 2. does the current plan survive the new truth?
        plan = self.repo.plan(case.plan_id) if case.plan_id else None
        if plan and plan.chosen and self._plan_invalidated_by(plan, new):
            self.repo.put_plan(plan.model_copy(update={"invalidated": True, "invalidation_reason": RejectionReason.INVALIDATED_BY_CONFIRMED_EVIDENCE}))
            case = self._transition(case, CaseAction.INVALIDATE_PLAN, plan_id=plan.id, donor=plan.chosen.donor_id)
            # 3. replan from the corrected inputs
            new_plan = self._evaluate(case)
            self.repo.put_plan(self.repo.plan(plan.id).model_copy(update={"superseded_by_id": new_plan.id}))
            case = case.model_copy(update={"plan_id": new_plan.id, "previous_plan_ids": (*case.previous_plan_ids, plan.id)})
            self.repo.put_case(case)
            case = self._transition(case, CaseAction.RECALCULATE_PLAN, plan_id=new_plan.id,
                                    chosen=new_plan.chosen.donor_id if new_plan.chosen else None,
                                    quantity=new_plan.chosen.quantity if new_plan.chosen else None)
        else:
            case = self._transition(case, CaseAction.PLAN_STILL_VALID, plan_id=case.plan_id)
        return self._mark_applied(case, command_id)

    def _plan_invalidated_by(self, plan: InterventionPlan, new_record: InventoryRecord) -> bool:
        """Re-run the evaluator on a scratch plan id; the plan is invalid if its
        chosen donor is no longer feasible under the corrected canonical inputs."""
        assert plan.chosen is not None
        probe = evaluate_candidates(self.repo, recipient_id=plan.recipient_id, item_id=plan.item_id, plan_id="probe", case_id=plan.case_id, evaluated_at=self.now())
        donor_now = next((c for c in probe.candidates if c.donor_id == plan.chosen.donor_id), None)
        touched = new_record.facility_id in (plan.chosen.donor_id, plan.recipient_id)
        return touched and (donor_now is None or not donor_now.feasible or donor_now.quantity != plan.chosen.quantity)

    def reject_evidence(self, case_id: str, evidence_id: str, *, rejected_by: str, note: str = "", command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        ev = self.repo.evidence(evidence_id)
        if ev.case_id != case.id:
            raise NotFound(f"evidence '{evidence_id}' does not belong to case '{case_id}'")
        if ev.state != EvidenceState.AWAITING_CONFIRMATION:
            raise IllegalTransition(f"evidence '{evidence_id}' is {ev.state.value}, not awaiting confirmation")
        next_state(case.state, CaseAction.REJECT_EVIDENCE)
        at = self._advance_clock()
        self.repo.put_evidence(ev.model_copy(update={"state": EvidenceState.REJECTED, "decided_at": at, "decided_by": rejected_by, "decision_note": note}))
        case = self._transition(case, CaseAction.REJECT_EVIDENCE, evidence_id=ev.id, rejected_by=rejected_by)
        return self._mark_applied(case, command_id)

    def approve(self, case_id: str, *, approved_by: str, command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        plan = self.current_plan(case_id)
        if plan is None or plan.chosen is None:
            raise InvariantViolation("cannot approve: the current plan has no feasible chosen donor")
        next_state(case.state, CaseAction.APPROVE)
        self._advance_clock()
        case = self._transition(case, CaseAction.APPROVE, plan_id=plan.id, approved_by=approved_by, donor=plan.chosen.donor_id, quantity=plan.chosen.quantity)
        return self._mark_applied(case, command_id)

    def dispatch(self, case_id: str, *, dispatched_by: str, command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        next_state(case.state, CaseAction.DISPATCH)
        plan = self.current_plan(case_id)
        assert plan and plan.chosen
        at = self._advance_clock()
        supply = IncomingSupply(
            id=self.repo.next_id("xfer"), destination_id=case.recipient_id, source_id=plan.chosen.donor_id, item_id=case.item_id,
            quantity=plan.chosen.quantity, expected_arrival_at=plan.chosen.expected_arrival_at, state=IncomingSupplyState.IN_TRANSIT,
            batch_id=plan.chosen.allocations[0].batch_id if plan.chosen.allocations else None,
            provenance=Provenance(source_type=SourceType.INTERVENTION, status=ProvenanceStatus.REPORTED, observed_at=at,
                                  source_ref=f"plan/{plan.id}", origin=self.actor_origin, note=f"dispatched by {dispatched_by}"),
        )
        self.repo.put_supply(supply)
        case = case.model_copy(update={"transfer_supply_id": supply.id})
        self.repo.put_case(case)
        case = self._transition(case, CaseAction.DISPATCH, supply_id=supply.id, donor=plan.chosen.donor_id, quantity=plan.chosen.quantity,
                                allocations=[a.model_dump(mode="json") for a in plan.chosen.allocations])
        return self._mark_applied(case, command_id)

    # ── verification (four-valued; only VERIFIED moves the case) ──────────

    def _record_verification(self, case: RecoveryCase, kind: VerificationKind, expected: str, observed: str | None, outcome: VerificationOutcome, by: str, note: str = "") -> tuple[RecoveryCase, VerificationRecord]:
        rec = VerificationRecord(id=self.repo.next_id("ver"), case_id=case.id, kind=kind, expected=expected, observed=observed,
                                 outcome=outcome, verified_at=self.now(), verified_by=by, note=note)
        self.repo.put_verification(rec)
        case = case.model_copy(update={"verification_ids": (*case.verification_ids, rec.id)})
        self.repo.put_case(case)
        return case, rec

    def verify_source(self, case_id: str, *, observed_quantity: int | None, verified_by: str, command_id: str | None = None) -> tuple[RecoveryCase, VerificationRecord]:
        return self._verify_quantity(case_id, VerificationKind.SOURCE, CaseAction.VERIFY_SOURCE, observed_quantity, verified_by, command_id)

    def verify_destination(self, case_id: str, *, observed_quantity: int | None, verified_by: str, command_id: str | None = None) -> tuple[RecoveryCase, VerificationRecord]:
        return self._verify_quantity(case_id, VerificationKind.DESTINATION, CaseAction.VERIFY_DESTINATION, observed_quantity, verified_by, command_id)

    def _verify_quantity(self, case_id: str, kind: VerificationKind, action: CaseAction, observed: int | None, by: str, command_id: str | None) -> tuple[RecoveryCase, VerificationRecord]:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done, self.repo.state().verifications[done.verification_ids[-1]]
        next_state(case.state, action)  # raises if not attemptable here
        plan = self.current_plan(case_id)
        assert plan and plan.chosen
        q = plan.chosen.quantity
        facility = plan.chosen.donor_id if kind == VerificationKind.SOURCE else case.recipient_id
        canonical = self.repo.canonical_inventory(facility, case.item_id)
        assert canonical is not None
        before = canonical.quantity
        expected = before - q if kind == VerificationKind.SOURCE else before + q
        self._advance_clock()
        outcome = classify_quantity(observed=observed, expected=expected, before=before)
        case, rec = self._record_verification(case, kind, expected=str(expected), observed=None if observed is None else str(observed), outcome=outcome, by=by,
                                              note=f"canonical {canonical.id} = {before} at verification time")
        if outcome == VerificationOutcome.VERIFIED:
            case = self._transition(case, action, verification_id=rec.id, expected=expected, observed=observed)
        else:
            self._audit(case, f"{action.value}:{outcome.value}", case.state, case.state, verification_id=rec.id, expected=expected, observed=observed)
        return self._mark_applied(case, command_id), rec

    def verify_batch(self, case_id: str, *, observed_batch_ids: list[str] | None, observed_quantity: int | None, verified_by: str, command_id: str | None = None) -> tuple[RecoveryCase, VerificationRecord]:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done, self.repo.state().verifications[done.verification_ids[-1]]
        next_state(case.state, CaseAction.VERIFY_BATCH)
        plan = self.current_plan(case_id)
        assert plan and plan.chosen
        expected_ids = [a.batch_id for a in plan.chosen.allocations]
        self._advance_clock()
        outcome = classify_batch(observed_batch_ids=observed_batch_ids, observed_quantity=observed_quantity, expected_batch_ids=expected_ids, expected_quantity=plan.chosen.quantity)
        case, rec = self._record_verification(case, VerificationKind.BATCH, expected=f"{expected_ids} × {plan.chosen.quantity}",
                                              observed=None if observed_batch_ids is None else f"{observed_batch_ids} × {observed_quantity}", outcome=outcome, by=verified_by)
        if outcome == VerificationOutcome.VERIFIED:
            case = self._transition(case, CaseAction.VERIFY_BATCH, verification_id=rec.id)
        else:
            self._audit(case, f"verify_batch:{outcome.value}", case.state, case.state, verification_id=rec.id)
        return self._mark_applied(case, command_id), rec

    # ── reconciliation: computes, never asserts ───────────────────────────

    def reconcile(self, case_id: str, *, command_id: str | None = None) -> tuple[RecoveryCase, ReconciliationRecord]:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done, self.repo.state().reconciliations[done.reconciliation_ids[-1]]
        next_state(case.state, CaseAction.RECONCILE)
        plan = self.current_plan(case_id)
        assert plan and plan.chosen

        vers = [self.repo.state().verifications[v] for v in case.verification_ids]
        verified = {v.kind: v for v in vers if v.outcome == VerificationOutcome.VERIFIED}
        if not all(k in verified for k in (VerificationKind.SOURCE, VerificationKind.DESTINATION, VerificationKind.BATCH)):
            at = self._advance_clock()
            rec = ReconciliationRecord(id=self.repo.next_id("rec"), case_id=case.id, at=at, outcome=ReconciliationOutcome.NOT_READY,
                                       originally_exposed_ids=case.originally_exposed_ids, still_exposed_ids=case.originally_exposed_ids,
                                       originally_exposed_refs=case.originally_exposed_refs, still_exposed_refs=case.originally_exposed_refs,
                                       protected_count=0, new_donor_record_id=None, new_recipient_record_id=None, note="verifications incomplete")
            self.repo.put_reconciliation(rec)
            case = case.model_copy(update={"reconciliation_ids": (*case.reconciliation_ids, rec.id)})
            self.repo.put_case(case)
            self._audit(case, "reconcile:not_ready", case.state, case.state, reconciliation_id=rec.id)
            return self._mark_applied(case, command_id), rec

        if (self.repo.canonical_inventory(plan.chosen.donor_id, case.item_id) is None
                or self.repo.canonical_inventory(case.recipient_id, case.item_id) is None
                or self.care_impact(case.recipient_id, case.item_id).status.value == "unavailable"):
            raise InvariantViolation("cannot reconcile: required canonical inventory or care impact is unavailable")
        at = self._advance_clock()

        # 1. verified physical counts become canonical (with lineage). The transfer is INSIDE them.
        def commit(facility_id: str, quantity: int, ver: VerificationRecord) -> InventoryRecord:
            old = self.repo.canonical_inventory(facility_id, case.item_id)
            assert old is not None
            new = InventoryRecord(id=self.repo.next_id(f"inv-{facility_id}-v"), facility_id=facility_id, item_id=case.item_id, quantity=quantity,
                                  canonical=True, supersedes_id=old.id,
                                  provenance=Provenance(source_type=SourceType.PHYSICAL_COUNT, status=ProvenanceStatus.VERIFIED, observed_at=ver.verified_at,
                                                        source_ref=f"verification/{ver.id}", origin=self.actor_origin, note=f"supersedes {old.id} ({old.quantity})"))
            self.repo.put_inventory(old.model_copy(update={"canonical": False, "superseded_by_id": new.id}))
            self.repo.put_inventory(new)
            return new

        donor_rec = commit(plan.chosen.donor_id, int(verified[VerificationKind.SOURCE].observed or 0), verified[VerificationKind.SOURCE])
        recip_rec = commit(case.recipient_id, int(verified[VerificationKind.DESTINATION].observed or 0), verified[VerificationKind.DESTINATION])

        # 2. the transfer supply is RECEIVED — it must not be credited again
        if case.transfer_supply_id:
            s = self.repo.state().supplies[case.transfer_supply_id]
            self.repo.put_supply(s.model_copy(update={"state": IncomingSupplyState.RECEIVED}))

        # 3. re-forecast from the verified canonical (as_of = verification time) and recompute exposure
        impact = self.care_impact(case.recipient_id, case.item_id)
        event_still = set(impact.exposed_event_ids)
        obligation_still = set(impact.exposed_obligation_ids)
        still_refs = tuple(r for r in case.originally_exposed_refs if (r.kind is ExposureKind.CARE_EVENT and r.id in event_still) or (r.kind is ExposureKind.CARE_OBLIGATION and r.id in obligation_still))
        # Backward compatibility for the original event-only fixture.
        still = tuple(r.id for r in still_refs if r.kind is ExposureKind.CARE_EVENT)
        coverage_restored = not still_refs
        requires_care_delivery = any(r.kind is ExposureKind.CARE_OBLIGATION for r in case.originally_exposed_refs)
        # Aggregate obligations are commitments whose actual delivery must be
        # verified after supply recovery. Event-row fixtures retain the legacy
        # compatibility path because their scheduled rows are already explicit
        # care evidence; a case with no exposed care refs is likewise complete.
        outcome = (ReconciliationOutcome.COVERAGE_RESTORED if coverage_restored and requires_care_delivery
                    else ReconciliationOutcome.CARE_PROTECTED if coverage_restored
                    else ReconciliationOutcome.STILL_EXPOSED)
        coverage_restored_count = len(case.originally_exposed_refs) - len(still_refs) if case.originally_exposed_refs else len(case.originally_exposed_ids) - len(still)
        protected_count = 0 if requires_care_delivery else coverage_restored_count
        rec = ReconciliationRecord(id=self.repo.next_id("rec"), case_id=case.id, at=at, outcome=outcome,
                                   originally_exposed_ids=case.originally_exposed_ids, still_exposed_ids=still,
                                   originally_exposed_refs=case.originally_exposed_refs, still_exposed_refs=still_refs,
                                   coverage_status=CoverageRecoveryStatus.COVERAGE_RESTORED if coverage_restored else CoverageRecoveryStatus.COVERAGE_NOT_RESTORED,
                                   coverage_restored_count=coverage_restored_count, protected_count=protected_count,
                                   new_donor_record_id=donor_rec.id, new_recipient_record_id=recip_rec.id,
                                   note=f"recipient re-forecast as of {recip_rec.provenance.observed_at.isoformat()}: coverage breach day {impact.coverage_breach_day}")
        self.repo.put_reconciliation(rec)
        case = case.model_copy(update={"reconciliation_ids": (*case.reconciliation_ids, rec.id)})
        self.repo.put_case(case)
        if outcome == ReconciliationOutcome.CARE_PROTECTED:
            case = case.model_copy(update={"care_protected_count": rec.protected_count})
            self.repo.put_case(case)
            case = self._transition(case, CaseAction.RECONCILE, reconciliation_id=rec.id, protected=rec.protected_count)
            # The state-machine transition is deliberately explicit even for
            # event-only compatibility cases; no care-obligation delivery is
            # required when the case has no aggregate obligations.
            case = self._transition(case, CaseAction.CARE_DELIVERY, reconciliation_id=rec.id, reason="no aggregate care obligations")
        elif outcome == ReconciliationOutcome.COVERAGE_RESTORED:
            case = self._transition(case, CaseAction.RECONCILE, reconciliation_id=rec.id,
                                    coverage_restored=rec.coverage_restored_count,
                                    care_delivery_required=True)
        else:
            self._audit(case, "reconcile:still_exposed", case.state, case.state, reconciliation_id=rec.id, still_exposed=len(still))
        return self._mark_applied(case, command_id), rec

    def record_care_delivery(self, case_id: str, *, exposure_kind: ExposureKind, exposure_id: str,
                             outcome: CareDeliveryOutcome, verified_by: str, source_ref: str,
                             note: str = "", command_id: str | None = None) -> tuple[RecoveryCase, CareDeliveryRecord]:
        case = self.repo.case(case_id)
        if command_id and command_id in case.applied_command_ids:
            rid = case.care_delivery_ids[-1]
            return case, self.repo.state().care_delivery[rid]
        ref = ExposureRef(kind=exposure_kind, id=exposure_id)
        if case.originally_exposed_refs and ref not in case.originally_exposed_refs:
            raise InvariantViolation(f"exposure '{exposure_id}' is not part of case '{case_id}'")
        required = {r for r in case.originally_exposed_refs if r.kind is ExposureKind.CARE_OBLIGATION}
        if required and case.state is not CaseState.COVERAGE_RESTORED:
            raise IllegalTransition("care delivery verification is available only after coverage is restored")
        if required and ref.kind is not ExposureKind.CARE_OBLIGATION:
            raise InvariantViolation("aggregate-obligation case requires delivery verification for its obligation refs")
        at = self._advance_clock()
        rec = CareDeliveryRecord(
            id=self.repo.next_id("care-delivery"), case_id=case.id, exposure=ref, outcome=outcome,
            verified_at=at, verified_by=verified_by, source_ref=source_ref,
            provenance=Provenance(source_type=SourceType.CARE_SCHEDULE, status=ProvenanceStatus.VERIFIED,
                                  observed_at=at, source_ref=source_ref, origin=self.actor_origin), note=note,
        )
        self.repo.put_care_delivery(rec)
        case = case.model_copy(update={"care_delivery_ids": (*case.care_delivery_ids, rec.id)})
        self.repo.put_case(case)
        delivered = {r.exposure for r in self.repo.state().care_delivery.values()
                     if r.case_id == case.id and r.outcome is CareDeliveryOutcome.DELIVERED}
        if required and outcome is CareDeliveryOutcome.DELIVERED and required.issubset(delivered):
            case = case.model_copy(update={"care_protected_count": len(required)})
            self.repo.put_case(case)
            case = self._transition(case, CaseAction.CARE_DELIVERY, exposure=ref.model_dump(), delivery_id=rec.id,
                                    protected=len(required))
        else:
            self._audit(case, f"care_delivery:{outcome.value}", case.state, case.state, exposure=ref.model_dump(), delivery_id=rec.id)
        return self._mark_applied(case, command_id), rec

    def close(self, case_id: str, *, closed_by: str, command_id: str | None = None) -> RecoveryCase:
        case = self.repo.case(case_id)
        if (done := self._idempotent(case, command_id)):
            return done
        # A case containing aggregated obligations needs explicit care outcome
        # evidence; stock reconciliation alone cannot claim care recovery.
        if case.originally_exposed_refs and any(r.kind is ExposureKind.CARE_OBLIGATION for r in case.originally_exposed_refs):
            delivered = {r.exposure for r in self.repo.state().care_delivery.values() if r.case_id == case.id and r.outcome is CareDeliveryOutcome.DELIVERED}
            required = {r for r in case.originally_exposed_refs if r.kind is ExposureKind.CARE_OBLIGATION}
            if not required.issubset(delivered):
                raise IllegalTransition("cannot close: care delivery outcome is unknown for one or more obligations")
        if case.state is not CaseState.CARE_PROTECTED:
            raise IllegalTransition("cannot close: case must be CARE_PROTECTED")
        next_state(case.state, CaseAction.CLOSE)
        at = self._advance_clock()
        case = case.model_copy(update={"closed_at": at})
        self.repo.put_case(case)
        case = self._transition(case, CaseAction.CLOSE, closed_by=closed_by, protected=case.care_protected_count)
        return self._mark_applied(case, command_id)

    # ── generic dispatcher for the API ────────────────────────────────────

    def advance(self, case_id: str, action: CaseAction, payload: dict, *, command_id: str | None = None,
                capability: str | None = None):
        if is_system_action(action):
            raise IllegalTransition(f"'{action.value}' is a system action and cannot be issued externally")
        actor = str(payload.get("actor", "demo-operator"))
        self.authorize_command(action=action, actor=actor, capability=capability)
        if action == CaseAction.PROPOSE:
            return self.propose(case_id, command_id=command_id)
        if action == CaseAction.APPROVE:
            return self.approve(case_id, approved_by=actor, command_id=command_id)
        if action == CaseAction.DISPATCH:
            return self.dispatch(case_id, dispatched_by=actor, command_id=command_id)
        if action == CaseAction.VERIFY_SOURCE:
            return self.verify_source(case_id, observed_quantity=payload.get("observed_quantity"), verified_by=actor, command_id=command_id)[0]
        if action == CaseAction.VERIFY_DESTINATION:
            return self.verify_destination(case_id, observed_quantity=payload.get("observed_quantity"), verified_by=actor, command_id=command_id)[0]
        if action == CaseAction.VERIFY_BATCH:
            return self.verify_batch(case_id, observed_batch_ids=payload.get("observed_batch_ids"), observed_quantity=payload.get("observed_quantity"), verified_by=actor, command_id=command_id)[0]
        if action == CaseAction.RECONCILE:
            if "care_protected" in payload:
                raise IllegalTransition("reconcile computes its outcome; it does not accept an asserted result")
            return self.reconcile(case_id, command_id=command_id)[0]
        if action == CaseAction.CLOSE:
            return self.close(case_id, closed_by=actor, command_id=command_id)
        raise IllegalTransition(f"'{action.value}' must be issued through its dedicated endpoint")

    def execute_command(self, case_id: str, action: CaseAction, payload: dict, *, command_id: str | None = None,
                        capability: str | None = None):
        """Named seam for future Auth-backed explicit operational commands."""
        return self.advance(case_id, action, payload, command_id=command_id, capability=capability)
