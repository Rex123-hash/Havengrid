"""Care Blast Radius (approved predicate), over two record shapes.

    uncovered   = [coverage_breach_at, recovery_at)          recovery_at = ∞ if none
    exposed(x)  ⇔ x.item_id == item
                ∧ x.time ∈ uncovered
                ∧ x.time within the forecast horizon
    unserved(x) ⇔ exposed(x) ∧ bucket(x) ≥ stockout_day

Two shapes are supported and counted together:
  * CareEvent       — one encounter (opaque id, no personal data). Counts 1.
  * CareObligation  — an aggregated session with `expected_attendance`.
                      Counts `expected_attendance`. This is the shape most
                      official sources can supply without exposing PHI.

Every aggregate is computed over rows. No total is ever stored as a fact.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

from ..domain.enums import CareCategory, ForecastStatus
from ..domain.models import CareEvent, CareImpact, CareObligation, CoverageAssessment, District, DerivedFrom


def _in_horizon(district: District, a: CoverageAssessment, at: datetime) -> bool:
    return 1 <= district.bucket_of(at) <= a.horizon_days


def _uncovered(district: District, a: CoverageAssessment) -> tuple[datetime, datetime] | None:
    if a.coverage_breach_at is None:
        return None
    upper = a.recovery_at if a.recovery_at is not None else district.day_end(a.horizon_days)
    return a.coverage_breach_at, upper


def exposed_events(district: District, a: CoverageAssessment, events: Iterable[CareEvent]) -> list[CareEvent]:
    win = _uncovered(district, a)
    if win is None:
        return []
    lo, hi = win
    rel = [e for e in events if e.facility_id == a.facility_id and e.item_id == a.item_id and _in_horizon(district, a, e.scheduled_at)]
    return sorted((e for e in rel if lo <= e.scheduled_at < hi), key=lambda e: (e.scheduled_at, e.id))


def exposed_obligations(district: District, a: CoverageAssessment, obligations: Iterable[CareObligation]) -> list[CareObligation]:
    win = _uncovered(district, a)
    if win is None:
        return []
    lo, hi = win
    rel = [o for o in obligations if o.facility_id == a.facility_id and o.item_id == a.item_id and _in_horizon(district, a, o.session_at)]
    return sorted((o for o in rel if lo <= o.session_at < hi), key=lambda o: (o.session_at, o.id))


def compute_care_impact(
    district: District,
    a: CoverageAssessment,
    events: Iterable[CareEvent],
    obligations: Iterable[CareObligation] = (),
) -> CareImpact:
    events = list(events)
    obligations = list(obligations)
    window_end = district.day_end(district.policy.planning_window_days)

    sched_events = [e for e in events if e.facility_id == a.facility_id and e.item_id == a.item_id and _in_horizon(district, a, e.scheduled_at) and e.scheduled_at < window_end]
    sched_obl = [o for o in obligations if o.facility_id == a.facility_id and o.item_id == a.item_id and _in_horizon(district, a, o.session_at) and o.session_at < window_end]

    lineage = DerivedFrom(record_type="care_impact_inputs", record_ids=tuple([a.inventory_record_id] if a.inventory_record_id else []) + tuple(e.id for e in events) + tuple(o.id for o in obligations), source_refs=tuple(e.provenance.source_ref for e in events) + tuple(o.provenance.source_ref for o in obligations), note="Exposure cannot be calculated without an available forecast" if a.status is ForecastStatus.UNAVAILABLE else "")
    if a.status is ForecastStatus.UNAVAILABLE:
        return CareImpact(facility_id=a.facility_id, item_id=a.item_id, status=ForecastStatus.UNAVAILABLE,
                          coverage_breach_day=None, recovery_day=None,
                          scheduled_in_window=len(sched_events) + sum(o.expected_attendance for o in sched_obl),
                          exposed_event_ids=(), exposed_obligation_ids=(), exposed_total=None,
                          exposed_by_category=None, exposed_units=None, unserved_event_ids=(),
                          unserved_obligation_ids=(), unserved_total=None, derived_from=lineage)

    ex_e = exposed_events(district, a, events)
    ex_o = exposed_obligations(district, a, obligations)

    def after_stockout(at: datetime) -> bool:
        return a.stockout_day is not None and district.bucket_of(at) >= a.stockout_day

    un_e = [e for e in ex_e if after_stockout(e.scheduled_at)]
    un_o = [o for o in ex_o if after_stockout(o.session_at)]

    by_cat: Counter[CareCategory] = Counter()
    for e in ex_e:
        by_cat[e.category] += 1
    for o in ex_o:
        by_cat[o.category] += o.expected_attendance

    return CareImpact(
        facility_id=a.facility_id,
        item_id=a.item_id,
        status=ForecastStatus.FORECAST,
        coverage_breach_day=a.coverage_breach_day,
        recovery_day=a.recovery_day,
        scheduled_in_window=len(sched_events) + sum(o.expected_attendance for o in sched_obl),
        exposed_event_ids=tuple(e.id for e in ex_e),
        exposed_obligation_ids=tuple(o.id for o in ex_o),
        exposed_total=len(ex_e) + sum(o.expected_attendance for o in ex_o),
        exposed_by_category={c: by_cat.get(c, 0) for c in CareCategory},
        exposed_units=sum(e.units_required for e in ex_e) + sum(o.expected_attendance * o.units_per_attendance for o in ex_o),
        unserved_event_ids=tuple(e.id for e in un_e),
        unserved_obligation_ids=tuple(o.id for o in un_o),
        unserved_total=len(un_e) + sum(o.expected_attendance for o in un_o),
        derived_from=lineage,
    )
