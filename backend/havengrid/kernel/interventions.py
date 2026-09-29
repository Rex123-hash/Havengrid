"""Intervention sizing, candidate evaluation, FEFO allocation, and ranking.

SIZING
    hold_through = (bucket of recipient's next credited scheduled supply) − 1,
                   else planning window
    q_min(a)     = max_{d ∈ [a, hold_through]} ( cover(d) − closing(d) )   a = arrival bucket
    q            = ceil_pack(q_min)             pack_size is a logistics fact on the Item

HARD FEASIBILITY — one primary reason per failed concern, no duplicates
    NO_VALID_ROUTE                    no Route donor→recipient (such pairs are not even candidates)
    DONOR_INVENTORY_UNKNOWN           donor forecast UNAVAILABLE
    DONOR_ALREADY_AT_RISK             donor coverage breaches inside its window at q = 0
    INSUFFICIENT_TRANSFERABLE_STOCK   q > transferable = min_{d≤W}(closing(d) − cover(d))
                                      (≡ donor would breach inside W after releasing q)
    ARRIVES_AFTER_RECIPIENT_BREACH    dispatch_ready + transit ≥ recipient.coverage_breach_at
    RECIPIENT_NOT_RECOVERED           recipient re-forecast with q credited at arrival still breaches ≤ hold_through

    W = min(bucket of donor's next credited scheduled supply, planning window)

FEFO ALLOCATION (inside the donor)
    sort eligible batches by expiry ascending (no-expiry last); consume from the
    earliest until q is allocated. The allocation is structured output.

RANKING (feasible only) — lexicographic, an explicit district redistribution policy
    1. expiry relief   (any allocated batch expires inside the forecast horizon)
    2. shortest transit
    3. largest post-transfer donor margin
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..domain.enums import CandidateVerdict, CurrentnessStatus, ForecastStatus, IncomingSupplyState, Origin, ProvenanceStatus, RejectionReason, SourceType
from ..domain.errors import InvariantViolation
from ..domain.models import (
    Batch,
    BatchAllocation,
    CandidateChecks,
    CoverageAssessment,
    District,
    IncomingSupply,
    InterventionCandidate,
    InterventionPlan,
    Provenance,
    RankComponents,
    DerivedFrom,
)
from ..store import InMemoryRepository
from .forecast import assess_coverage, quantity_to_hold, round_up_to_pack, transferable_through_window

_FAR_FUTURE = datetime(9999, 1, 1, tzinfo=timezone.utc)


def forecast_for(
    repo: InMemoryRepository,
    facility_id: str,
    item_id: str,
    *,
    extra_supplies: list[IncomingSupply] | None = None,
    inventory_override: int | None = None,
) -> CoverageAssessment:
    """Forecast a facility from its canonical record (anchored at that record's as_of)."""
    district = repo.state().district
    canonical = repo.canonical_inventory(facility_id, item_id)
    if inventory_override is not None:
        starting, as_of, rec_id = inventory_override, canonical.provenance.observed_at if canonical else district.forecast_at, None
    else:
        starting = canonical.quantity if canonical else None
        as_of = canonical.provenance.observed_at if canonical else district.forecast_at
        rec_id = canonical.id if canonical else None
    return assess_coverage(
        district,
        facility_id=facility_id,
        item_id=item_id,
        starting_inventory=starting,
        profile=repo.demand_profile(facility_id, item_id),
        events=repo.care_events_for(facility_id, item_id),
        supplies=list(repo.supplies_for(facility_id, item_id)) + list(extra_supplies or []),
        as_of=as_of,
        inventory_record_id=rec_id,
        obligations=repo.care_obligations_for(facility_id, item_id),
    )


def next_credited_supply_day(district: District, supplies: list[IncomingSupply]) -> int | None:
    days = [
        district.bucket_of(s.expected_arrival_at)
        for s in supplies
        if s.state in (IncomingSupplyState.SCHEDULED, IncomingSupplyState.IN_TRANSIT) and district.bucket_of(s.expected_arrival_at) >= 1
    ]
    return min(days) if days else None


def hold_through_day(district: District, recipient_supplies: list[IncomingSupply]) -> int:
    nxt = next_credited_supply_day(district, recipient_supplies)
    return nxt - 1 if nxt is not None else district.policy.planning_window_days


def protection_window(district: District, donor_supplies: list[IncomingSupply]) -> int:
    nxt = next_credited_supply_day(district, donor_supplies)
    w = district.policy.planning_window_days
    return min(nxt, w) if nxt is not None else w


def allocate_fefo(batches: list[Batch], quantity: int) -> tuple[BatchAllocation, ...]:
    ordered = sorted(batches, key=lambda b: (b.expires_at is None, b.expires_at or _FAR_FUTURE, b.id))
    remaining = quantity
    out: list[BatchAllocation] = []
    for b in ordered:
        if remaining <= 0:
            break
        take = min(b.quantity, remaining)
        if take > 0:
            out.append(BatchAllocation(batch_id=b.id, quantity=take, expires_at=b.expires_at))
            remaining -= take
    return tuple(out)


def simulated_transfer(district: District, *, supply_id: str, donor_id: str, recipient_id: str, item_id: str, quantity: int, arrival_at: datetime, batch_id: str | None) -> IncomingSupply:
    return IncomingSupply(
        id=supply_id, destination_id=recipient_id, source_id=donor_id, item_id=item_id, quantity=quantity,
        expected_arrival_at=arrival_at, state=IncomingSupplyState.SCHEDULED, batch_id=batch_id,
        provenance=Provenance(source_type=SourceType.INTERVENTION, status=ProvenanceStatus.PROPOSED,
                              observed_at=district.forecast_at, source_ref="kernel.interventions/simulated", origin=Origin.SIMULATED_COUNTERFACTUAL),
    )


def evaluate_candidates(repo: InMemoryRepository, *, recipient_id: str, item_id: str, plan_id: str, case_id: str, evaluated_at: datetime) -> InterventionPlan:
    st = repo.state()
    district = st.district
    policy = district.policy
    item = repo.item(item_id)

    recipient = forecast_for(repo, recipient_id, item_id)
    if recipient.status is not ForecastStatus.FORECAST:
        raise InvariantViolation("cannot evaluate intervention: recipient inventory or demand forecast is unavailable",
                                 recipient_id=recipient_id, item_id=item_id)
    hold = hold_through_day(district, repo.supplies_for(recipient_id, item_id))
    horizon_end = district.day_end(policy.horizon_days)

    candidates: list[InterventionCandidate] = []
    for route in repo.routes_into(recipient_id):
        donor_id = route.from_id
        donor = repo.facility(donor_id)
        reasons: list[RejectionReason] = []
        if donor_id == recipient_id:
            reasons.append(RejectionReason.DONOR_IS_RECIPIENT)
        if donor.currentness in (CurrentnessStatus.UNKNOWN, CurrentnessStatus.UNVERIFIED):
            reasons.append(RejectionReason.FACILITY_UNVERIFIED)

        # ── timing ──
        lead = policy.dispatch_lead_hours[donor.tier]
        dispatch_ready_at = district.forecast_at + timedelta(hours=float(lead))
        arrival_at = dispatch_ready_at + timedelta(hours=float(route.transit_hours))
        arrival_day = max(1, district.bucket_of(arrival_at))
        arrives_before = recipient.coverage_breach_at is None or arrival_at < recipient.coverage_breach_at
        if not arrives_before:
            reasons.append(RejectionReason.ARRIVES_AFTER_RECIPIENT_BREACH)

        # ── sizing ──
        quantity = round_up_to_pack(quantity_to_hold(recipient, credited_on_day=arrival_day, hold_through_day=hold), item.pack_size)

        # ── donor safety: one primary reason ──
        donor_now = forecast_for(repo, donor_id, item_id)
        known = donor_now.status == ForecastStatus.FORECAST
        window = protection_window(district, repo.supplies_for(donor_id, item_id))
        transferable = 0
        post_breach: int | None = None
        not_at_risk = False
        if not known:
            reasons.append(RejectionReason.DONOR_INVENTORY_UNKNOWN)
        else:
            not_at_risk = donor_now.coverage_breach_day is None or donor_now.coverage_breach_day > window
            transferable = transferable_through_window(donor_now, window_days=window)
            on_hand = donor_now.starting_inventory or 0
            # Diagnostic only (the hard check is `quantity <= transferable`). A donor
            # that cannot even physically release q is "breached" on day 0.
            post_breach = 0 if quantity > on_hand else forecast_for(repo, donor_id, item_id, inventory_override=on_hand - quantity).coverage_breach_day
            if not not_at_risk:
                reasons.append(RejectionReason.DONOR_ALREADY_AT_RISK)
            elif quantity > transferable:
                reasons.append(RejectionReason.INSUFFICIENT_TRANSFERABLE_STOCK)
        margin = transferable - quantity

        # ── batch allocation (FEFO) ──
        allocations = allocate_fefo(repo.batches_for(donor_id, item_id), quantity) if known else ()
        expiry_relief = any(a.expires_at is not None and a.expires_at <= horizon_end for a in allocations)

        # ── recipient recovery ──
        sim = simulated_transfer(district, supply_id=f"sim-{donor_id}", donor_id=donor_id, recipient_id=recipient_id, item_id=item_id,
                                 quantity=quantity, arrival_at=arrival_at, batch_id=allocations[0].batch_id if allocations else None)
        recipient_after = forecast_for(repo, recipient_id, item_id, extra_supplies=[sim])
        recovers = recipient_after.coverage_breach_day is None or recipient_after.coverage_breach_day > hold
        if not recovers:
            reasons.append(RejectionReason.RECIPIENT_NOT_RECOVERED)

        checks = CandidateChecks(
            route_exists=True, donor_inventory_known=known, donor_not_already_at_risk=not_at_risk,
            sufficient_transferable_stock=known and quantity <= transferable,
            arrives_before_recipient_breach=arrives_before, recipient_recovers=recovers,
        )
        candidates.append(InterventionCandidate(
            id=f"{plan_id}:{donor_id}", donor_id=donor_id, recipient_id=recipient_id, item_id=item_id, quantity=quantity,
            donor_inventory=donor_now.starting_inventory, transferable=transferable, donor_protection_window_days=window,
            donor_coverage_breach_day=donor_now.coverage_breach_day, donor_post_transfer_breach_day=post_breach, donor_post_transfer_margin=margin,
            distance_km=route.distance_km, transit_hours=route.transit_hours, dispatch_ready_at=dispatch_ready_at,
            expected_arrival_at=arrival_at, arrival_day=arrival_day, recipient_breach_at=recipient.coverage_breach_at,
            recipient_post_transfer_breach_day=recipient_after.coverage_breach_day, allocations=allocations, expiry_relief=expiry_relief,
            feasible=not reasons, checks=checks, rejection_reasons=tuple(reasons), rank=None,
            rank_components=RankComponents(expiry_relief=expiry_relief, transit_hours=route.transit_hours, post_transfer_margin=margin),
            verdict=CandidateVerdict.REJECTED,
            derived_from=DerivedFrom(record_type="intervention_candidate_inputs", record_ids=tuple(x for x in (donor_now.inventory_record_id, recipient.inventory_record_id) if x), source_refs=(route.provenance.source_ref,)),
        ))

    def key(c: InterventionCandidate):
        rc = c.rank_components
        return (0 if rc.expiry_relief else 1, rc.transit_hours, -rc.post_transfer_margin, c.donor_id)

    feasible = sorted((c for c in candidates if c.feasible), key=key)
    verdicts = {c.id: (i, CandidateVerdict.CHOSEN if i == 1 else CandidateVerdict.HELD) for i, c in enumerate(feasible, start=1)}
    final = tuple(
        (c.model_copy(update={"rank": verdicts[c.id][0], "verdict": verdicts[c.id][1]}) if c.id in verdicts else c)
        for c in sorted(candidates, key=lambda c: (not c.feasible, key(c)))
    )
    chosen = next((c for c in final if c.verdict == CandidateVerdict.CHOSEN), None)
    return InterventionPlan(
        id=plan_id, case_id=case_id, recipient_id=recipient_id, item_id=item_id,
        required_quantity=round_up_to_pack(quantity_to_hold(recipient, credited_on_day=1, hold_through_day=hold), item.pack_size),
        hold_through_day=hold, chosen=chosen, candidates=final, evaluated_at=evaluated_at,
        derived_from=DerivedFrom(record_type="intervention_plan_inputs", record_ids=tuple(c.id for c in final), source_refs=tuple(r.provenance.source_ref for r in repo.routes_into(recipient_id))),
    )


EXPLANATIONS: dict[RejectionReason, str] = {
    RejectionReason.NO_VALID_ROUTE: "No emergency transfer route exists to the recipient.",
    RejectionReason.DONOR_IS_RECIPIENT: "A facility cannot donate to itself.",
    RejectionReason.DONOR_INVENTORY_UNKNOWN: "The donor has no canonical inventory record; its safety cannot be established.",
    RejectionReason.DONOR_ALREADY_AT_RISK: "The donor's own coverage breaches inside its protection window even without a transfer.",
    RejectionReason.INSUFFICIENT_TRANSFERABLE_STOCK: "The donor's transferable surplus is smaller than the required quantity; releasing it would breach the donor's own coverage.",
    RejectionReason.ARRIVES_AFTER_RECIPIENT_BREACH: "The transfer would arrive after the recipient's coverage breach.",
    RejectionReason.RECIPIENT_NOT_RECOVERED: "Even with the transfer the recipient does not stay covered until its next scheduled supply.",
    RejectionReason.INVALIDATED_BY_CONFIRMED_EVIDENCE: "Confirmed field evidence changed the inputs this plan depended on.",
    RejectionReason.FACILITY_UNVERIFIED: "The facility identity is not currently verified for operational donor use.",
}


def explain(reason: RejectionReason) -> str:
    return EXPLANATIONS[reason]
