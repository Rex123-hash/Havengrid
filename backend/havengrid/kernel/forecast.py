"""Deterministic coverage forecast (approved at the Phase 0A gate, with the
time-semantics correction).

TEMPORAL MODEL — explicit boundaries, no ad-hoc rules
    Day d is the half-open bucket B(d) = [T0 + (d−1)·24h, T0 + d·24h).
    * Incoming supply is credited at its actual arrival timestamp. Because
      demand settles at bucket END, a supply arriving anywhere inside B(d) is
      on the shelf when B(d) settles.
    * Scheduled care events contribute their units to the bucket containing
      their scheduled timestamp.
    * Demand for B(d) settles at day_end(d).
    * Coverage is evaluated at day_end(d), after settlement:
          covered(d) ⇔ closing(d) ≥ cover(d),  cover(d) = Σ demand(d+1 … d+min_cover)
    * The coverage state established at day_end(d) governs bucket B(d+1).

DERIVED TIMESTAMPS
    coverage_breach_day b = min { d : ¬covered(d) }        coverage_breach_at = day_end(b)
    stockout_day        s = min { d : closing(d) < 0 }      stockout_at        = day_end(s)
    recovery_day        r = min { d > b : covered(d) }      recovery_at        = day_end(r)
    uncovered interval    = [coverage_breach_at, recovery_at)   ⇒ buckets b+1 … r

    The bucket in which a restoring supply lands is still governed by the
    previous (uncovered) evaluation until it settles. That is conservative and
    deliberate: the model never claims coverage before it has been evaluated.

AS-OF ANCHORING
    A forecast is anchored at `as_of` (default T0). The canonical inventory is
    the level AT `as_of`. Buckets that ended before `as_of` are not settled
    again; supplies that arrived at or before `as_of` are not credited again
    (they are already inside the observed quantity). This is what makes a
    post-verification re-forecast honest: 223 observed at T0+6h already
    contains the 80-unit transfer, so only the future 200-unit scheduled
    replenishment is credited.

TWO CONCEPTS, NEVER CONFLATED
    coverage breach — cannot cover the next `min_cover_days` of care.
    stockout        — physically cannot dispense.

Missing canonical inventory or baseline → UNAVAILABLE. Unknown is never healthy.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from ..domain.enums import ForecastStatus, IncomingSupplyState, Origin, ProvenanceStatus, SourceType
from ..domain.models import (
    CareEvent,
    CareObligation,
    CoverageAssessment,
    DemandProfile,
    District,
    IncomingSupply,
    ProjectionRow,
    Provenance,
    DerivedFrom,
)

KERNEL_REF = "kernel.forecast/v1-coverage"


def demand_series(district: District, profile: DemandProfile | None, events: Iterable[CareEvent], *, facility_id: str, item_id: str, obligations: Iterable[CareObligation] = ()) -> tuple[list[int], list[str]]:
    p = district.policy
    length = p.horizon_days + p.min_cover_days
    demand = [0] * (length + 1)
    drivers: list[str] = []
    if profile is None:
        return demand, ["no baseline demand profile"]

    n = len(profile.daily)
    for d in range(1, length + 1):
        demand[d] += profile.daily[d - 1] if d <= n else profile.daily[-1]
    drivers.append(f"baseline walk-in demand: {profile.shape_note} [{profile.provenance.source_ref}]")
    if n < length:
        drivers.append(f"baseline seeded for {n} days; {profile.daily[-1]}/day carried forward to day {length}")

    units = count = 0
    for ev in events:
        if ev.facility_id != facility_id or ev.item_id != item_id:
            continue
        day = district.bucket_of(ev.scheduled_at)
        if 1 <= day <= length:
            demand[day] += ev.units_required
            units += ev.units_required
            count += 1
    if count:
        drivers.append(f"{count} scheduled care events add {units} units")

    # Aggregated obligations: expected_attendance encounters on session_at.
    o_units = o_count = o_att = 0
    for ob in obligations:
        if ob.facility_id != facility_id or ob.item_id != item_id:
            continue
        day = district.bucket_of(ob.session_at)
        if 1 <= day <= length:
            u = ob.expected_attendance * ob.units_per_attendance
            demand[day] += u
            o_units += u
            o_att += ob.expected_attendance
            o_count += 1
    if o_count:
        drivers.append(f"{o_count} aggregated care obligations ({o_att} expected attendances) add {o_units} units")
    return demand, drivers


def credit_series(district: District, supplies: Iterable[IncomingSupply], *, as_of: datetime) -> tuple[dict[int, int], list[str]]:
    credits: dict[int, int] = defaultdict(int)
    drivers: list[str] = []
    for s in supplies:
        day = district.bucket_of(s.expected_arrival_at)
        live = s.state in (IncomingSupplyState.SCHEDULED, IncomingSupplyState.IN_TRANSIT)
        if live and s.expected_arrival_at <= as_of:
            drivers.append(f"supply {s.id} ({s.quantity}) arrived at or before as_of — assumed inside the observed quantity, not credited")
        elif live and 1 <= day <= district.policy.horizon_days:
            credits[day] += s.quantity
            drivers.append(f"incoming {s.quantity} credited in day {day} (arrives {s.expected_arrival_at.isoformat()}) [{s.provenance.source_ref}]")
        elif s.state == IncomingSupplyState.CANCELLED:
            drivers.append(f"supply {s.id} ({s.quantity}) is CANCELLED — not credited")
        elif s.state == IncomingSupplyState.RECEIVED:
            drivers.append(f"supply {s.id} ({s.quantity}) already RECEIVED — reflected in canonical inventory, not credited")
    return credits, drivers


def assess_coverage(
    district: District,
    *,
    facility_id: str,
    item_id: str,
    starting_inventory: int | None,
    profile: DemandProfile | None,
    events: Iterable[CareEvent],
    supplies: Iterable[IncomingSupply],
    as_of: datetime | None = None,
    inventory_record_id: str | None = None,
    obligations: Iterable[CareObligation] = (),
) -> CoverageAssessment:
    p = district.policy
    anchor = as_of or district.forecast_at
    prov = Provenance(
        source_type=SourceType.KERNEL,
        status=ProvenanceStatus.PREDICTED,
        observed_at=anchor,
        source_ref=KERNEL_REF,
        origin=Origin.MODEL_DERIVED,   # the computation is real; its INPUTS carry their own origins
        note="daily buckets; coverage evaluated at bucket end; breach = closing < forward cover; stockout = closing < 0",
    )
    base = dict(
        facility_id=facility_id,
        item_id=item_id,
        forecast_at=district.forecast_at,
        as_of=anchor,
        inventory_record_id=inventory_record_id,
        horizon_days=p.horizon_days,
        min_cover_days=p.min_cover_days,
        provenance=prov,
        derived_from=DerivedFrom(record_type="coverage_inputs", record_ids=tuple(x for x in (inventory_record_id, *(e.id for e in events), *(o.id for o in obligations), *(s.id for s in supplies)) if x), source_refs=tuple(x.provenance.source_ref for x in (*events, *obligations, *supplies))),
    )
    demand, d_drivers = demand_series(district, profile, events, facility_id=facility_id, item_id=item_id, obligations=obligations)

    if starting_inventory is None or profile is None:
        why = "no canonical inventory record" if starting_inventory is None else "no baseline demand profile"
        return CoverageAssessment(
            **base, status=ForecastStatus.UNAVAILABLE, starting_inventory=starting_inventory,
            coverage_breach_day=None, coverage_breach_at=None, stockout_day=None, stockout_at=None,
            recovery_day=None, recovery_at=None, projection=(),
            drivers=(f"{why} — forecast UNAVAILABLE; this is NOT 'healthy'", *d_drivers),
        )

    credits, c_drivers = credit_series(district, supplies, as_of=anchor)
    first_day = max(1, district.bucket_of(anchor))   # buckets already settled before as_of are skipped

    rows: list[ProjectionRow] = []
    level = starting_inventory
    breach = stockout = recovery = None
    for d in range(first_day, p.horizon_days + 1):
        opening = level
        credit = credits.get(d, 0)
        level = opening + credit - demand[d]
        cover = sum(demand[d + 1 : d + 1 + p.min_cover_days])
        covered = level >= cover
        rows.append(ProjectionRow(day=d, opening=opening, credit=credit, demand=demand[d], closing=level, cover_required=cover, covered=covered))
        if breach is None and not covered:
            breach = d
        if stockout is None and level < 0:
            stockout = d
        if breach is not None and recovery is None and d > breach and covered:
            recovery = d

    end = lambda day: None if day is None else district.day_end(day)  # noqa: E731
    drivers = [
        f"starting inventory {starting_inventory} as of {anchor.isoformat()} ({inventory_record_id or 'simulated'})",
        f"forward cover = next {p.min_cover_days} days of demand (district policy)",
        *d_drivers, *c_drivers,
    ]
    if first_day > 1:
        drivers.append(f"buckets 1–{first_day-1} settled before as_of and are not re-applied")
    if breach is None:
        drivers.append(f"coverage holds through day {p.horizon_days}")
    else:
        row = next(r for r in rows if r.day == breach)
        drivers.append(f"coverage breach on day {breach}: closing {row.closing} < cover {row.cover_required}")
    if stockout is not None:
        drivers.append(f"physical stockout on day {stockout}")
    if recovery is not None:
        drivers.append(f"coverage restored at end of day {recovery}")

    return CoverageAssessment(
        **base, status=ForecastStatus.FORECAST, starting_inventory=starting_inventory,
        coverage_breach_day=breach, coverage_breach_at=end(breach),
        stockout_day=stockout, stockout_at=end(stockout),
        recovery_day=recovery, recovery_at=end(recovery),
        projection=tuple(rows), drivers=tuple(drivers),
    )


def quantity_to_hold(a: CoverageAssessment, *, credited_on_day: int, hold_through_day: int) -> int:
    """Smallest extra quantity credited on `credited_on_day` keeping every day in
    [credited_on_day, hold_through_day] covered. 0 if already covered."""
    need = 0
    for row in a.projection:
        if credited_on_day <= row.day <= hold_through_day:
            need = max(need, row.cover_required - row.closing)
    return max(0, need)


def round_up_to_pack(quantity: int, pack_size: int) -> int:
    return 0 if quantity <= 0 else ((quantity + pack_size - 1) // pack_size) * pack_size


def transferable_through_window(a: CoverageAssessment, *, window_days: int) -> int:
    """max q with ∀ d ∈ [1, W]: closing(d) − q ≥ cover(d)  ⇔  min_d (closing(d) − cover(d))."""
    margins = [r.closing - r.cover_required for r in a.projection if 1 <= r.day <= window_days]
    return min(margins) if margins else 0
