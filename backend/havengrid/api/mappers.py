"""Domain → DTO mapping. Kept out of the routes so both stay readable."""

from __future__ import annotations

from ..domain.models import (
    AuditEvent,
    CareEvent,
    CareImpact,
    CoverageAssessment,
    District,
    EvidenceRecord,
    Facility,
    InterventionCandidate,
    InterventionPlan,
    InventoryRecord,
    Item,
    ReconciliationRecord,
    RecoveryCase,
    SupplyLink,
    VerificationRecord,
    DistrictProfile,
    DistrictCommodityStockSignal,
    DistrictReadiness,
    CareDeliveryRecord,
    ProgrammeActivity,
    RouteObservation,
)
from ..kernel.interventions import explain
from ..kernel.state_machine import legal_actions
from ..store import InMemoryRepository
from . import schemas as S


import re

_COUNT_RE = re.compile(r"(\d+) days? before T0")


def days_since_count(repo: InMemoryRepository, facility_id: str, item_id: str) -> int | None:
    """Fixture inventory notes encode the last physical count; a confirmed or
    verified record IS a count (0 days). No record → None (unknown, not fresh)."""
    rec = repo.canonical_inventory(facility_id, item_id)
    if rec is None:
        return None
    if rec.provenance.status.value == "verified":
        return 0
    m = _COUNT_RE.search(rec.provenance.note)
    return int(m.group(1)) if m else None


def provenance(p) -> S.ProvenanceOut:
    return S.ProvenanceOut(source_type=p.source_type.value, status=p.status.value, observed_at=p.observed_at, source_ref=p.source_ref,
                           origin=p.origin.value, confidence=p.confidence, note=p.note, publisher=p.publisher, source_period=p.source_period,
                           retrieved_at=p.retrieved_at, geographic_granularity=p.geographic_granularity, source_hash=p.source_hash,
                           quality_flags=[x.value for x in p.quality_flags])


def derived(d):
    return None if d is None else S.DerivedFromOut(record_type=d.record_type, record_ids=list(d.record_ids), source_refs=list(d.source_refs), note=d.note)


def facility(f: Facility) -> S.FacilityOut:
    return S.FacilityOut(id=f.id, name=f.name, short_name=f.short_name, tier=f.tier, x=f.position.x, y=f.position.y,
                         block=f.block, official_identifier=f.official_identifier, source_ref=f.source_ref,
                         source_date=f.source_date, currentness=f.currentness.value, coordinate_source=f.coordinate_source, facility_type=f.facility_type,
                         latitude=f.latitude, longitude=f.longitude, coordinate_provenance=provenance(f.coordinate_provenance) if f.coordinate_provenance else None)


def link(l: SupplyLink) -> S.LinkOut:
    return S.LinkOut(from_id=l.from_id, to_id=l.to_id)


def item(i: Item) -> S.ItemOut:
    return S.ItemOut(id=i.id, name=i.name, form=i.form, unit=i.unit, pack_size=i.pack_size,
                     physical_dispatch_unit=i.physical_dispatch_unit,
                     dose_rules=[x.model_dump(mode="json") for x in i.dose_rules])


def district(d: District) -> S.DistrictOut:
    p = d.policy
    return S.DistrictOut(id=d.id, name=d.name, region=d.region, timezone=d.timezone, forecast_at=d.forecast_at,
                         policy=S.PolicyOut(min_cover_days=p.min_cover_days, planning_window_days=p.planning_window_days, horizon_days=p.horizon_days,
                                            dispatch_lead_hours={k.value: v for k, v in p.dispatch_lead_hours.items()},
                                            policy_minimum_cover_days=p.policy_minimum_cover_days,
                                            havengrid_continuity_threshold_days=p.havengrid_continuity_threshold_days))


def forecast(a: CoverageAssessment, d: District) -> S.ForecastOut:
    w = d.policy.planning_window_days
    demand = sum(r.demand for r in a.projection if r.day <= w) if a.projection else None
    gap = (demand - a.starting_inventory) if (demand is not None and a.starting_inventory is not None) else None
    return S.ForecastOut(
        facility_id=a.facility_id, item_id=a.item_id, status=a.status, as_of=a.as_of, inventory_record_id=a.inventory_record_id,
        starting_inventory=a.starting_inventory, coverage_breach_day=a.coverage_breach_day, coverage_breach_at=a.coverage_breach_at,
        stockout_day=a.stockout_day, stockout_at=a.stockout_at, recovery_day=a.recovery_day, recovery_at=a.recovery_at,
        projected_demand_window=demand, gap_window=gap,
        projection=[S.ProjectionRowOut(**r.model_dump()) for r in a.projection], drivers=list(a.drivers), derived_from=derived(a.derived_from),
    )


def care_impact(c: CareImpact) -> S.CareImpactOut:
    return S.CareImpactOut(facility_id=c.facility_id, status=c.status, coverage_breach_day=c.coverage_breach_day, recovery_day=c.recovery_day,
                           scheduled_in_window=c.scheduled_in_window, exposed_total=c.exposed_total, exposed_by_category=c.exposed_by_category,
                           exposed_event_ids=list(c.exposed_event_ids), exposed_obligation_ids=list(c.exposed_obligation_ids), exposed_units=c.exposed_units,
                           unserved_total=c.unserved_total, unserved_event_ids=list(c.unserved_event_ids), unserved_obligation_ids=list(c.unserved_obligation_ids), derived_from=derived(c.derived_from))


def care_event(e: CareEvent, d: District, impact: CareImpact) -> S.CareEventOut:
    return S.CareEventOut(id=e.id, facility_id=e.facility_id, category=e.category, scheduled_at=e.scheduled_at, day=d.bucket_of(e.scheduled_at),
                          units_required=e.units_required, description=e.description,
                          exposed=None if impact.status.value == "unavailable" else e.id in impact.exposed_event_ids,
                          unserved=None if impact.status.value == "unavailable" else e.id in impact.unserved_event_ids)


def candidate(c: InterventionCandidate, repo: InMemoryRepository) -> S.CandidateOut:
    rc = c.rank_components
    return S.CandidateOut(
        donor_id=c.donor_id, donor_name=repo.facility(c.donor_id).name, quantity=c.quantity, donor_inventory=c.donor_inventory,
        transferable=c.transferable, donor_protection_window_days=c.donor_protection_window_days, donor_coverage_breach_day=c.donor_coverage_breach_day,
        donor_post_transfer_breach_day=c.donor_post_transfer_breach_day, donor_post_transfer_margin=c.donor_post_transfer_margin,
        distance_km=c.distance_km, transit_hours=c.transit_hours, dispatch_ready_at=c.dispatch_ready_at, expected_arrival_at=c.expected_arrival_at,
        arrival_day=c.arrival_day, recipient_post_transfer_breach_day=c.recipient_post_transfer_breach_day,
        allocations=[S.AllocationOut(**a.model_dump()) for a in c.allocations], expiry_relief=c.expiry_relief, feasible=c.feasible,
        checks=c.checks.model_dump(), rejection_reasons=list(c.rejection_reasons), explanations=[explain(r) for r in c.rejection_reasons],
        rank=c.rank, rank_components={"expiry_relief": rc.expiry_relief, "transit_hours": rc.transit_hours, "post_transfer_margin": rc.post_transfer_margin},
        verdict=c.verdict, derived_from=derived(c.derived_from),
    )


def plan(p: InterventionPlan, repo: InMemoryRepository) -> S.PlanOut:
    return S.PlanOut(id=p.id, case_id=p.case_id, recipient_id=p.recipient_id, required_quantity=p.required_quantity, hold_through_day=p.hold_through_day,
                     chosen_donor_id=p.chosen.donor_id if p.chosen else None, candidates=[candidate(c, repo) for c in p.candidates],
                     evaluated_at=p.evaluated_at, invalidated=p.invalidated, invalidation_reason=p.invalidation_reason, superseded_by_id=p.superseded_by_id,
                     derived_from=derived(p.derived_from))


def inventory(r: InventoryRecord) -> S.InventoryRecordOut:
    return S.InventoryRecordOut(id=r.id, facility_id=r.facility_id, quantity=r.quantity, canonical=r.canonical, supersedes_id=r.supersedes_id,
                                superseded_by_id=r.superseded_by_id, evidence_id=r.evidence_id, provenance=provenance(r.provenance))


def evidence(e: EvidenceRecord) -> S.EvidenceOut:
    return S.EvidenceOut(id=e.id, case_id=e.case_id, facility_id=e.facility_id, observed_quantity=e.observed_quantity, confidence=e.confidence,
                         source_type=e.source_type.value, captured_via=e.captured_via, observed_at=e.observed_at, state=e.state,
                         canonical_quantity_at_submission=e.canonical_quantity_at_submission, canonical_record_id_at_submission=e.canonical_record_id_at_submission,
                         evidence_class=e.evidence_class, committed_record_id=e.committed_record_id, decided_at=e.decided_at, decided_by=e.decided_by)


def verification(v: VerificationRecord) -> S.VerificationOut:
    return S.VerificationOut(id=v.id, kind=v.kind, expected=v.expected, observed=v.observed, outcome=v.outcome, verified_at=v.verified_at, verified_by=v.verified_by, note=v.note)


def reconciliation(r: ReconciliationRecord) -> S.ReconciliationOut:
    return S.ReconciliationOut(id=r.id, at=r.at, outcome=r.outcome, originally_exposed_ids=list(r.originally_exposed_ids),
                               still_exposed_ids=list(r.still_exposed_ids), protected_count=r.protected_count, note=r.note,
                               originally_exposed_refs=[{"kind": x.kind.value, "id": x.id} for x in r.originally_exposed_refs],
                               still_exposed_refs=[{"kind": x.kind.value, "id": x.id} for x in r.still_exposed_refs],
                               coverage_status=r.coverage_status, coverage_restored_count=r.coverage_restored_count)


def audit(a: AuditEvent) -> S.AuditOut:
    return S.AuditOut(seq=a.seq, at=a.at, action=a.action, from_state=a.from_state, to_state=a.to_state, detail=a.detail)


def case(c: RecoveryCase) -> S.CaseOut:
    return S.CaseOut(id=c.id, district_id=c.district_id, recipient_id=c.recipient_id, item_id=c.item_id, state=c.state,
                     legal_actions=legal_actions(c.state), plan_id=c.plan_id, previous_plan_ids=list(c.previous_plan_ids),
                     evidence_ids=list(c.evidence_ids), verification_ids=list(c.verification_ids), reconciliation_ids=list(c.reconciliation_ids),
                     originally_exposed_ids=list(c.originally_exposed_ids),
                     originally_exposed_refs=[{"kind": x.kind.value, "id": x.id} for x in c.originally_exposed_refs],
                     care_delivery_ids=list(c.care_delivery_ids), transfer_supply_id=c.transfer_supply_id,
                     care_protected_count=c.care_protected_count, closed_at=c.closed_at)


def district_profile(p: DistrictProfile) -> S.DistrictProfileOut:
    return S.DistrictProfileOut(
        id=p.id, display_name=p.display_name, region=p.region, state_or_region=p.state_or_region, country=p.country, timezone=p.timezone,
        official_codes=p.official_codes, source_catalog=[S.SourceCatalogEntryOut(**x.model_dump()) for x in p.source_catalog],
        facility_source_family=p.facility_source_family, stock_source_families=list(p.stock_source_families),
        programme_source_families=list(p.programme_source_families), policy_source_ref=p.policy_source_ref,
        coordinate_policy=p.coordinate_policy, supported_items=list(p.supported_items), facility_source_config=p.facility_source_config,
        programme_source_config=p.programme_source_config, commodity_profiles=list(p.commodity_profiles), policy_profile=p.policy_profile,
        supported_languages=list(p.supported_languages), data_freshness_rules=p.data_freshness_rules,
    )


def stock_signal(s: DistrictCommodityStockSignal) -> S.DistrictCommodityStockSignalOut:
    return S.DistrictCommodityStockSignalOut(
        id=s.id, district_id=s.district_id, item_id=s.item_id, period=s.period,
        opening_balance=s.opening_balance, received=s.received, distributed=s.distributed,
        unusable=s.unusable, available=s.available, unit=s.unit, geographic_granularity=s.geographic_granularity,
        source_ref=s.source_ref, source_hash=s.source_hash, retrieved_at=s.retrieved_at,
        quality_flags=[x.value for x in s.quality_flags], provenance=provenance(s.provenance),
    )


def readiness(r: DistrictReadiness) -> S.DistrictReadinessOut:
    return S.DistrictReadinessOut(
        district_id=r.district_id, facility_roster=r.facility_roster, programme_activity=r.programme_activity,
        district_stock_context=r.district_stock_context, facility_inventory=r.facility_inventory,
        routes=r.routes, care_obligations=r.care_obligations, policy=r.policy, reasons=list(r.reasons),
    )


def programme_activity(r: ProgrammeActivity) -> S.ProgrammeActivityOut:
    return S.ProgrammeActivityOut(id=r.id, district_id=r.district_id, period=r.period, indicator=r.indicator,
                                  value=r.value, unit=r.unit, evidence_grade=r.evidence_grade, basis=r.basis,
                                  allocation_method=r.allocation_method, uncertainty=r.uncertainty,
                                  derived_from=list(r.derived_from), provenance=provenance(r.provenance))


def route_observation(r: RouteObservation) -> S.RouteObservationOut:
    return S.RouteObservationOut(id=r.id, from_id=r.from_id, to_id=r.to_id, distance_km=r.distance_km,
                                 duration_hours=r.duration_hours, static_duration_hours=r.static_duration_hours,
                                 retrieved_at=r.retrieved_at, provider=r.provider, request_hash=r.request_hash,
                                 status=r.status.value, provenance=provenance(r.provenance), error=r.error)


def care_delivery(r: CareDeliveryRecord) -> S.CareDeliveryOut:
    return S.CareDeliveryOut(id=r.id, case_id=r.case_id, exposure={"kind": r.exposure.kind.value, "id": r.exposure.id},
                             outcome=r.outcome, verified_at=r.verified_at, verified_by=r.verified_by, source_ref=r.source_ref, note=r.note)
