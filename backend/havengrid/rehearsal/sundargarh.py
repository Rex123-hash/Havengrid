"""One real-grounded Sundargarh rehearsal for judge-facing numbers.

The source boundary is intentionally visible in this module:

* district stock and KPI percentages come from captured public AMB responses;
* facility identities/blocks come from the Odisha directory;
* stock counts and care-session allocation are controlled rehearsal evidence;
* forecasts, exposure, transfer sizing, ranking and recovery are kernel output.

This module does not alter the production bootstrap or the frozen frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..domain.enums import (CareCategory, CaseState, FacilityTier,
                            EvidenceGrade, IncomingSupplyState, Origin,
                            ProvenanceStatus, ReadinessStatus, SourceType, CareDeliveryOutcome)
from ..domain.models import (Batch, CareObligation, CoverPolicy, DemandProfile, District,
                             DistrictReadiness, IncomingSupply, InventoryRecord, Item,
                             Provenance, RecoveryCase, Route, SupplyLink)
from ..official.activity import load_sundargarh_kpi_activity
from ..official.facilities import sundargarh_facility_set
from ..official.sundargarh import sundargarh_ifa_slice
from ..ingest.google_routes import load_captured_route_matrix
from ..service import HavenGridService
from ..store import InMemoryRepository, ScenarioState
from .contracts import DonorFact, FactClass, JudgeScenarioContract, NumberRange, RouteFact

T0 = datetime(2026, 9, 12, 2, 30, tzinfo=timezone.utc)
CASE_ID = "case-lahunipada-ifa-red-rehearsal-001"
ITEM_ID = "ifa-red-60mg-500mcg"
RECIPIENT_ID = "chc-lahunipada"
CASSETTE = Path(__file__).resolve().parents[3] / "data" / "raw" / "live" / "google_routes" / "sundargarh-lahunipada-matrix.json"


def _p(source_type: SourceType, status: ProvenanceStatus, ref: str, *, origin: Origin,
       observed_at: datetime = T0, note: str = "", source_period: str | None = None,
       retrieved_at: datetime | None = None) -> Provenance:
    return Provenance(source_type=source_type, status=status, observed_at=observed_at,
                      source_ref=ref, origin=origin, note=note, source_period=source_period,
                      retrieved_at=retrieved_at)


def _day(day: int, hours: float = 0) -> datetime:
    return T0 + timedelta(days=day - 1, hours=hours)


def build_sundargarh_rehearsal() -> ScenarioState:
    """Build the initial state; recipient inventory is deliberately unknown."""
    profile, item, signals = sundargarh_ifa_slice()
    policy = CoverPolicy(
        min_cover_days=3, planning_window_days=14, horizon_days=30,
        dispatch_lead_hours={FacilityTier.PHC: Decimal("2"), FacilityTier.CHC: Decimal("2"), FacilityTier.WAREHOUSE: Decimal("24")},
        havengrid_continuity_threshold_days=3,
        provenance=_p(SourceType.DISTRICT_POLICY, ProvenanceStatus.OBSERVED, "rehearsal/policy/cover-3-days",
                       origin=Origin.USER_SUPPLIED_EVIDENCE, note="Controlled rehearsal policy; validate against district SOP before operational use."),
    )
    district = District(id="sundargarh", name="Sundargarh", region="Odisha · India", timezone="Asia/Kolkata", forecast_at=T0, policy=policy)
    st = ScenarioState(district=district, district_profile=profile)
    st.items[item.id] = item
    st.district_stock_signals.update({x.id: x for x in signals})
    st.programme_activity.update({x.id: x for x in load_sundargarh_kpi_activity()})
    facilities = sundargarh_facility_set()
    st.facilities.update({x.id: x for x in facilities})
    st.links.extend(SupplyLink(from_id="dhh-sundargarh", to_id=x.id) for x in facilities if x.id != "dhh-sundargarh")

    # Captured Google responses are persisted first, then admitted as Route
    # facts only when the provider returned a usable value.
    observations = load_captured_route_matrix(CASSETTE)
    st.route_observations.update({x.id: x for x in observations})
    for observation in observations:
        if observation.distance_km is not None and observation.duration_hours is not None:
            st.routes[(observation.from_id, observation.to_id)] = Route(
                from_id=observation.from_id, to_id=observation.to_id,
                distance_km=observation.distance_km, transit_hours=observation.duration_hours,
                static_transit_hours=observation.static_duration_hours, provider=observation.provider,
                request_hash=observation.request_hash, status=observation.status,
                retrieved_at=observation.retrieved_at, provenance=observation.provenance,
            )

    # All facility stock values in this scenario are controlled field counts.
    # They are not AMB district totals and are never described as government stock.
    def inventory(id_: str, facility: str, quantity: int, ref: str, note: str) -> None:
        st.inventory[id_] = InventoryRecord(
            id=id_, facility_id=facility, item_id=ITEM_ID, quantity=quantity, canonical=True,
            provenance=_p(SourceType.PHYSICAL_COUNT, ProvenanceStatus.VERIFIED, ref, origin=Origin.USER_SUPPLIED_EVIDENCE,
                          observed_at=T0, note=f"REHEARSAL_FIELD_OBSERVATION; {note}"),
        )

    inventory("rehearsal-inv-bonai-v1", "sdh-bonai", 120, "rehearsal-field/sdh-bonai/initial", "controlled shelf count used for the initial donor proposal")
    inventory("rehearsal-inv-panposh-v1", "sdh-panposh", 220, "rehearsal-field/sdh-panposh/initial", "controlled shelf count used as held donor")
    inventory("rehearsal-inv-laing-v1", "chc-laing", 210, "rehearsal-field/chc-laing/initial", "controlled shelf count used as held donor")
    inventory("rehearsal-inv-mangaspur-v1", "chc-mangaspur", 260, "rehearsal-field/chc-mangaspur/initial", "controlled shelf count used as held donor")

    def demand(facility: str, daily: int, note: str) -> None:
        st.demand[(facility, ITEM_ID)] = DemandProfile(
            facility_id=facility, item_id=ITEM_ID, daily=tuple([daily] * 14), shape_note=f"REHEARSAL_MODEL_INPUT; {note}",
            provenance=_p(SourceType.CONSUMPTION_HISTORY, ProvenanceStatus.INFERRED, f"rehearsal-model/demand/{facility}",
                           origin=Origin.MODEL_DERIVED, note="Controlled rate for deterministic rehearsal; no HMIS facility consumption export admitted."),
        )

    demand(RECIPIENT_ID, 4, "4 tablets/day controlled dispensing rate")
    demand("sdh-bonai", 4, "4 tablets/day controlled dispensing rate")
    demand("sdh-panposh", 5, "5 tablets/day controlled dispensing rate")
    demand("chc-laing", 5, "5 tablets/day controlled dispensing rate")
    demand("chc-mangaspur", 6, "6 tablets/day controlled dispensing rate")
    demand("dhh-sundargarh", 10, "10 tablets/day controlled warehouse rate")

    def supply(id_: str, destination: str, quantity: int, day: int, source: str) -> None:
        st.supplies[id_] = IncomingSupply(
            id=id_, destination_id=destination, source_id=source, item_id=ITEM_ID, quantity=quantity,
            expected_arrival_at=_day(day), state=IncomingSupplyState.SCHEDULED,
            provenance=_p(SourceType.SCHEDULED_INDENT, ProvenanceStatus.REPORTED, f"rehearsal-indent/{destination}/{day}",
                           origin=Origin.USER_SUPPLIED_EVIDENCE, note="Controlled rehearsal supply schedule."),
        )

    supply("rehearsal-supply-lahunipada-001", RECIPIENT_ID, 120, 14, "dhh-sundargarh")
    supply("rehearsal-supply-bonai-001", "sdh-bonai", 50, 15, "dhh-sundargarh")
    supply("rehearsal-supply-panposh-001", "sdh-panposh", 100, 12, "dhh-sundargarh")
    supply("rehearsal-supply-laing-001", "chc-laing", 100, 15, "dhh-sundargarh")
    supply("rehearsal-supply-mangaspur-001", "chc-mangaspur", 100, 15, "dhh-sundargarh")

    def batch(id_: str, facility: str, quantity: int, expires: datetime | None) -> None:
        st.batches[id_] = Batch(id=id_, facility_id=facility, item_id=ITEM_ID, quantity=quantity, expires_at=expires,
                                provenance=_p(SourceType.DIGITAL_LEDGER, ProvenanceStatus.REPORTED, f"rehearsal-batch/{id_}",
                                               origin=Origin.USER_SUPPLIED_EVIDENCE, note="Controlled rehearsal batch register."))

    batch("IFA-BONAI-EXP-001", "sdh-bonai", 60, _day(10))
    batch("IFA-BONAI-001", "sdh-bonai", 60, datetime(2027, 3, 31, tzinfo=timezone.utc))
    batch("IFA-PANPOSH-001", "sdh-panposh", 220, datetime(2027, 3, 31, tzinfo=timezone.utc))
    batch("IFA-LAING-001", "chc-laing", 210, datetime(2027, 3, 31, tzinfo=timezone.utc))
    batch("IFA-MANGASPUR-001", "chc-mangaspur", 260, datetime(2027, 3, 31, tzinfo=timezone.utc))

    kpi_refs = tuple(st.programme_activity)
    obligation = CareObligation(
        id="obligation-lahunipada-anc-2025-05-001", facility_id=RECIPIENT_ID, category=CareCategory.MATERNAL,
        session_at=_day(8, 2), item_id=ITEM_ID, expected_attendance=13, units_per_attendance=1,
        description="Aggregate ANC session; no individual patient records are present.",
        provenance=_p(SourceType.PROGRAMME_ACTIVITY, ProvenanceStatus.INFERRED, "rehearsal-model/obligation/lahunipada-anc",
                      origin=Origin.MODEL_DERIVED, note="Derived from AMB KPI coverage percentage plus a controlled aggregate session range; no patient list."),
        units_basis=item.units_rule.source_ref if item.units_rule else "AMB policy",
        estimated_population_min=11, estimated_population_max=15, tablets_required_min=11, tablets_required_max=15,
        uncertainty_note="11–15 aggregate supplementation obligations; deterministic kernel uses midpoint 13 for this rehearsal.",
        evidence_grade=EvidenceGrade.PROGRAMME_ESTIMATED,
        basis="AMB KPI May 2025 HMIS 1.2.4 (84.4% district percentage) + national 1 tablet/day antenatal policy",
        allocation_method="controlled facility session range allocated to Lahunipada; midpoint used for deterministic forecast",
        numeric_basis_origin="REHEARSAL_ASSUMPTION", public_programme_basis="AMB",
        facility_denominator_status="UNKNOWN",
    )
    st.care_obligations[obligation.id] = obligation
    st.readiness = DistrictReadiness(
        district_id="sundargarh", facility_roster=ReadinessStatus.READY, programme_activity=ReadinessStatus.READY,
        district_stock_context=ReadinessStatus.READY, facility_inventory=ReadinessStatus.PARTIAL,
        routes=ReadinessStatus.READY, care_obligations=ReadinessStatus.READY, policy=ReadinessStatus.READY,
        reasons=("Recipient facility inventory begins UNKNOWN and is established only by a labelled rehearsal field observation.",
                 "AMB public stock is district aggregate context; it is not facility inventory."),
    )
    st.cases[CASE_ID] = RecoveryCase(id=CASE_ID, district_id="sundargarh", recipient_id=RECIPIENT_ID,
                                     item_id=ITEM_ID, state=CaseState.FORECASTED, opened_at=T0)
    return st


def build_sundargarh_rehearsal_checkpoint() -> ScenarioState:
    """Replay only the four legitimate commands needed for the browser start.

    Bonai's contradictory observation remains awaiting confirmation; its
    canonical 120-tablet record and original plan are untouched.
    """
    service = HavenGridService(InMemoryRepository(build_sundargarh_rehearsal), actor_origin=Origin.USER_SUPPLIED_EVIDENCE)
    _, recipient = service.submit_evidence(CASE_ID, facility_id=RECIPIENT_ID, observed_quantity=30,
                                           confidence=Decimal("0.95"), captured_via="controlled rehearsal shelf count",
                                           evidence_class="REHEARSAL_FIELD_OBSERVATION")
    service.confirm_evidence(CASE_ID, recipient.id, confirmed_by="rehearsal-pharmacist",
                             note="Controlled judge rehearsal input")
    service.propose(CASE_ID)
    service.submit_evidence(CASE_ID, facility_id="sdh-bonai", observed_quantity=20,
                            confidence=Decimal("0.92"), captured_via="controlled rehearsal shelf count",
                            evidence_class="REHEARSAL_FIELD_OBSERVATION")
    return service.repo.state()


@dataclass
class RehearsalRun:
    service: HavenGridService
    contract: JudgeScenarioContract
    route_observations: tuple[Any, ...]


def _route_fact(observation: Any) -> RouteFact:
    return RouteFact(donor_id=observation.from_id, recipient_id=observation.to_id,
                     distance_km=observation.distance_km, duration_hours=observation.duration_hours,
                     static_duration_hours=observation.static_duration_hours, retrieved_at=observation.retrieved_at,
                     provider=observation.provider, request_hash=observation.request_hash, status=observation.status.value,
                     provenance=observation.provenance.model_dump(mode="json"))


def _contract(service: HavenGridService, *, initial_plan: Any, corrected_plan: Any,
              initial_evidence: Any, donor_evidence: Any, reconciliation: Any,
              delivery: Any, routes: tuple[Any, ...], initial_forecast: Any,
              initial_impact: Any) -> JudgeScenarioContract:
    st = service.repo.state()
    case = st.cases[CASE_ID]
    recipient = st.facilities[RECIPIENT_ID]
    forecast = service.forecast(RECIPIENT_ID, ITEM_ID)
    impact = service.care_impact(RECIPIENT_ID, ITEM_ID)
    obligation = next(iter(st.care_obligations.values()))
    kpi = next(x for x in st.programme_activity.values() if "pregnant" in x.indicator)
    route_by_donor = {x.from_id: x for x in routes}
    def donor_fact(c: Any) -> DonorFact:
        return DonorFact(donor_id=c.donor_id, donor_name=st.facilities[c.donor_id].name, feasible=c.feasible,
                         rank=c.rank, verdict=c.verdict.value, quantity=c.quantity,
                         rejection_reasons=[x.value for x in c.rejection_reasons],
                         route=_route_fact(route_by_donor[c.donor_id]) if c.donor_id in route_by_donor else None,
                         donor_inventory=c.donor_inventory, transferable=c.transferable,
                         post_transfer_margin=c.donor_post_transfer_margin, expiry_relief=c.expiry_relief)
    chosen_initial = initial_plan.chosen.donor_id if initial_plan.chosen else None
    chosen_replanned = corrected_plan.chosen.donor_id if corrected_plan.chosen else None
    return JudgeScenarioContract(
        scenario_id=CASE_ID, rehearsal_label="REAL PUBLIC CONTEXT + CONTROLLED FIELD OBSERVATIONS + MODEL-DERIVED OUTPUTS",
        district={"id": st.district.id, "name": st.district.name, "region": st.district.region, "forecast_at": st.district.forecast_at},
        recipient_facility=st.facilities[RECIPIENT_ID].model_dump(mode="json"),
        commodity={"id": ITEM_ID, "name": st.items[ITEM_ID].name, "form": st.items[ITEM_ID].form, "unit": st.items[ITEM_ID].unit,
                   "pack_size": st.items[ITEM_ID].pack_size, "calculation_unit": "tablet",
                   "physical_dispatch_unit": st.items[ITEM_ID].physical_dispatch_unit,
                   "pack_size_basis": "UNKNOWN physical pack data; pack_size=1 is calculation granularity only",
                   "dose_rules": [x.model_dump(mode="json") for x in st.items[ITEM_ID].dose_rules]},
        district_public_stock_context={"period": "2025-2026", "signals": [x.model_dump(mode="json") for x in st.district_stock_signals.values()],
                                       "origin": "OFFICIAL_PUBLIC_DATA", "granularity": "district"},
        stock_source_date="2026-06-03", facility_observation={"initial_status": "UNKNOWN", "observation_class": initial_evidence.evidence_class,
                                                                "recipient_quantity": initial_evidence.observed_quantity, "confirmed": initial_evidence.state.value == "confirmed",
                                                                "source_ref": initial_evidence.committed_record_id and st.inventory[initial_evidence.committed_record_id].provenance.source_ref,
                                                                "confirmed_by": initial_evidence.decided_by},
        programme_obligation={"id": obligation.id, "programme": "antenatal_ifa", "period": "2025-2026:May", "session_at": obligation.session_at,
                              "estimated_population": {"low": obligation.estimated_population_min, "high": obligation.estimated_population_max},
                              "tablets_required": {"low": obligation.tablets_required_min, "high": obligation.tablets_required_max},
                              "deterministic_midpoint": obligation.expected_attendance, "uncertainty": obligation.uncertainty_note,
                              "evidence_grade": obligation.evidence_grade.value, "basis": obligation.basis,
                              "allocation_method": obligation.allocation_method, "kpi_value": kpi.value, "kpi_source": kpi.provenance.source_ref,
                              "numeric_basis_origin": obligation.numeric_basis_origin,
                              "public_programme_basis": obligation.public_programme_basis,
                              "facility_denominator_status": obligation.facility_denominator_status,
                              "allocation_method_comparison": [
                                  {"method": "controlled_facility_session_range", "result": "11–15 aggregate obligations", "used": True,
                                   "reason": "Explicit rehearsal session range; midpoint 13 is the only deterministic arithmetic input."},
                                  {"method": "district_percentage_preserving", "result": "UNKNOWN", "used": False,
                                   "reason": "84.4% is a district percentage without a Lahunipada denominator, so it cannot honestly allocate a facility count."},
                              ]},
        forecast={"initial": {"starting_inventory": initial_forecast.starting_inventory, "projection": [x.model_dump(mode="json") for x in initial_forecast.projection],
                               "coverage_breach_day": initial_forecast.coverage_breach_day, "stockout_day": initial_forecast.stockout_day,
                               "recovery_day": initial_forecast.recovery_day, "exposed_total": initial_impact.exposed_total},
                  "post_recovery": {"starting_inventory": forecast.starting_inventory, "projection": [x.model_dump(mode="json") for x in forecast.projection],
                                    "coverage_breach_day": forecast.coverage_breach_day, "stockout_day": forecast.stockout_day,
                                    "recovery_day": forecast.recovery_day, "exposed_total": impact.exposed_total}},
        programme_demand=sum(x.demand for x in initial_forecast.projection if x.day <= st.district.policy.planning_window_days),
        baseline_demand={"facility_id": RECIPIENT_ID, "daily_units": 4, "window_days": st.district.policy.planning_window_days,
                         "total_units": 56, "unit": "tablet", "classification": FactClass.REHEARSAL_ASSUMPTION.value,
                         "assumption": "Controlled 4-tablet/day rehearsal dispensing rate; no facility consumption export admitted."},
        coverage_breach_day=initial_forecast.coverage_breach_day, stockout_day=initial_forecast.stockout_day,
        exposure_range=NumberRange(low=Decimal(obligation.estimated_population_min or obligation.expected_attendance), high=Decimal(obligation.estimated_population_max or obligation.expected_attendance), unit="aggregate obligations"),
        transfer_quantity=corrected_plan.chosen.quantity if corrected_plan.chosen else 0,
        transfer_quantity_unit="tablet", physical_dispatch_unit=st.items[ITEM_ID].physical_dispatch_unit,
        transfer_quantity_note="47 is a calculation quantity; physical pack/issue unit is UNKNOWN and must be resolved before operational dispatch.",
        initial_donor_candidates=[donor_fact(c) for c in initial_plan.candidates], donor_candidates=[donor_fact(c) for c in corrected_plan.candidates], initial_chosen_donor=chosen_initial,
        evidence_correction={"donor_id": donor_evidence.facility_id, "observation_class": donor_evidence.evidence_class,
                             "initial_quantity": donor_evidence.canonical_quantity_at_submission, "corrected_quantity": donor_evidence.observed_quantity,
                             "confirmed": donor_evidence.state.value == "confirmed", "confirmed_by": donor_evidence.decided_by,
                             "invalidated_plan_id": initial_plan.id},
        replanned_donor=chosen_replanned,
        coverage_recovery={"status": reconciliation.coverage_status.value, "reconciliation": reconciliation.outcome.value,
                           "coverage_restored_count": reconciliation.coverage_restored_count,
                           "reconciliation_protected_count": reconciliation.protected_count,
                           "protected_count": case.care_protected_count, "still_exposed": [x.model_dump(mode="json") for x in reconciliation.still_exposed_refs],
                           "recipient_post_transfer_inventory": st.inventory[reconciliation.new_recipient_record_id].quantity if reconciliation.new_recipient_record_id else None},
        care_delivery_verification={"id": delivery.id, "exposure": delivery.exposure.model_dump(mode="json"), "outcome": delivery.outcome.value,
                                    "source_ref": delivery.source_ref, "provenance": delivery.provenance.origin.value},
        lifecycle=[x.action for x in service.repo.audit_for(CASE_ID)], provenance_labels={
            "district_stock_context": FactClass.REAL_PUBLIC.value, "facility_identity": FactClass.REAL_PUBLIC.value,
            "facility_observation": FactClass.REHEARSAL_EVIDENCE.value, "programme_obligation": FactClass.REHEARSAL_ASSUMPTION.value,
            "route": FactClass.LIVE_EXTERNAL_API.value, "forecast_and_plan": FactClass.MODEL_DERIVED.value,
            "care_delivery": FactClass.REHEARSAL_EVIDENCE.value,
        }, fact_classifications={
            "schema_version": FactClass.MODEL_DERIVED,
            "commodity": FactClass.REAL_PUBLIC,
            "commodity.pack_size": FactClass.REHEARSAL_ASSUMPTION,
            "commodity.pack_size_basis": FactClass.UNKNOWN,
            "commodity.physical_dispatch_unit": FactClass.UNKNOWN,
            "physical_dispatch_unit": FactClass.UNKNOWN,
            "transfer_quantity_unit": FactClass.REAL_PUBLIC,
            "transfer_quantity_note": FactClass.UNKNOWN,
            "district.forecast_at": FactClass.REHEARSAL_ASSUMPTION,
            "programme_obligation": FactClass.REHEARSAL_ASSUMPTION,
            "programme_obligation.kpi_value": FactClass.REAL_PUBLIC,
            "programme_obligation.kpi_source": FactClass.REAL_PUBLIC,
            "programme_obligation.period": FactClass.REAL_PUBLIC,
            "programme_obligation.facility_denominator_status": FactClass.UNKNOWN,
            "recipient_facility.coordinate_provenance": FactClass.LIVE_EXTERNAL_API,
            "recipient_facility.coordinate_provenance.retrieved_at": FactClass.UNKNOWN,
            "recipient_facility.coordinate_provenance.observed_at": FactClass.UNKNOWN,
            "recipient_facility.latitude": FactClass.LIVE_EXTERNAL_API,
            "recipient_facility.longitude": FactClass.LIVE_EXTERNAL_API,
            **{f"{group}.{i}.{field}": cls
               for group, candidates in (("initial_donor_candidates", initial_plan.candidates), ("donor_candidates", corrected_plan.candidates))
               for i, candidate in enumerate(candidates)
               for field, cls in (("route", FactClass.LIVE_EXTERNAL_API), ("donor_inventory", FactClass.REHEARSAL_EVIDENCE), ("donor_name", FactClass.REAL_PUBLIC), ("donor_id", FactClass.REAL_PUBLIC))},
            "scenario_id": FactClass.REHEARSAL_ASSUMPTION, "mode": FactClass.REHEARSAL_ASSUMPTION,
            "rehearsal_label": FactClass.REHEARSAL_ASSUMPTION,
            "district": FactClass.REAL_PUBLIC, "recipient_facility": FactClass.REAL_PUBLIC,
            "commodity.policy": FactClass.REAL_PUBLIC, "district_public_stock_context": FactClass.REAL_PUBLIC,
            "stock_source_date": FactClass.REAL_PUBLIC,
            "facility_observation": FactClass.REHEARSAL_EVIDENCE,
            "programme_obligation.public_programme_basis": FactClass.REAL_PUBLIC,
            "programme_obligation.estimated_population": FactClass.REHEARSAL_ASSUMPTION,
            "baseline_demand": FactClass.REHEARSAL_ASSUMPTION,
            "forecast": FactClass.MODEL_DERIVED, "programme_demand": FactClass.MODEL_DERIVED,
            "coverage_breach_day": FactClass.MODEL_DERIVED, "stockout_day": FactClass.MODEL_DERIVED,
            "exposure_range": FactClass.MODEL_DERIVED, "transfer_quantity": FactClass.MODEL_DERIVED,
            "initial_donor_candidates": FactClass.MODEL_DERIVED, "donor_candidates": FactClass.MODEL_DERIVED,
            "evidence_correction": FactClass.REHEARSAL_EVIDENCE, "coverage_recovery": FactClass.MODEL_DERIVED,
            "care_delivery_verification": FactClass.REHEARSAL_EVIDENCE, "unknown_facts": FactClass.UNKNOWN,
            "route_observations": FactClass.LIVE_EXTERNAL_API, "initial_chosen_donor": FactClass.MODEL_DERIVED,
            "replanned_donor": FactClass.MODEL_DERIVED, "lifecycle": FactClass.MODEL_DERIVED,
            "generated_at": FactClass.MODEL_DERIVED,
        }, derived_from={
            "schema_version": ["JudgeScenarioContract:0.8.1"],
            "forecast": list(initial_forecast.derived_from.record_ids if initial_forecast.derived_from else ()) + ["demand:rehearsal-model-demand-chc-lahunipada"],
            "programme_demand": ["forecast.initial.projection"], "coverage_breach_day": ["forecast.initial.projection"],
            "stockout_day": ["forecast.initial.projection"], "exposure_range": ["obligation-lahunipada-anc-2025-05-001"],
            "transfer_quantity": ["intervention-plan:recalculated"], "initial_donor_candidates": ["route_observations", "inventory", "forecast"],
            "donor_candidates": ["route_observations", "inventory:evidence/ev-002", "forecast"], "coverage_recovery": ["verification", "reconciliation"],
            "initial_chosen_donor": ["intervention-plan:initial"], "replanned_donor": ["intervention-plan:recalculated"],
            "lifecycle": ["audit"], "generated_at": ["runtime-clock"],
        }, assumption_notes={
            "commodity.pack_size": "One tablet is arithmetic granularity only; official issue packaging is unavailable.",
            "district.forecast_at": "Fixed scenario clock for deterministic rehearsal replay.",
            "programme_obligation": "Controlled aggregate session; no public facility denominator or patient identities are available.",
            "scenario_id": "Stable identifier for this controlled rehearsal scenario.",
            "mode": "This contract intentionally describes a rehearsal, not an operational claim.",
            "rehearsal_label": "The label makes public context, controlled observations, and model outputs explicit.",
            "programme_obligation.estimated_population": "Controlled facility-session rehearsal range because public KPI has no Lahunipada denominator.",
            "baseline_demand": "Controlled 4-tablet/day rate used to exercise the deterministic kernel; it is not observed dispensing history.",
        }, unknown_facts=["Official facility-level IFA inventory is not public in this capture.", "Current HMIS facility consumption and patient-level care records are not present.", "Coordinates are corroborating OSM points; official HFR coordinates are not captured.", "Physical dispatch pack size is unknown; 47 is a calculation quantity requiring operational pack conversion."], generated_at=datetime.now(timezone.utc),
    )


def run_sundargarh_rehearsal() -> RehearsalRun:
    repo = InMemoryRepository(build_sundargarh_rehearsal)
    service = HavenGridService(repo, actor_origin=Origin.USER_SUPPLIED_EVIDENCE)
    # Establish the recipient from an explicit, labelled rehearsal observation.
    _, initial_evidence = service.submit_evidence(CASE_ID, facility_id=RECIPIENT_ID, observed_quantity=30,
                                                   confidence=Decimal("0.95"), captured_via="controlled rehearsal shelf count",
                                                   evidence_class="REHEARSAL_FIELD_OBSERVATION")
    service.confirm_evidence(CASE_ID, initial_evidence.id, confirmed_by="rehearsal-pharmacist", note="Controlled judge rehearsal input")
    service.propose(CASE_ID)
    initial_plan = service.current_plan(CASE_ID)
    assert initial_plan is not None
    initial_evidence = service.repo.evidence(initial_evidence.id)
    initial_forecast = service.forecast(RECIPIENT_ID, ITEM_ID)
    initial_impact = service.care_impact(RECIPIENT_ID, ITEM_ID)
    # Reality Lens: the initial donor appears safe, then a human observation
    # invalidates it and the deterministic evaluator chooses a replacement.
    _, donor_evidence = service.submit_evidence(CASE_ID, facility_id="sdh-bonai", observed_quantity=20,
                                                confidence=Decimal("0.92"), captured_via="controlled rehearsal shelf count",
                                                evidence_class="REHEARSAL_FIELD_OBSERVATION")
    service.confirm_evidence(CASE_ID, donor_evidence.id, confirmed_by="rehearsal-pharmacist", note="Controlled donor correction")
    donor_evidence = service.repo.evidence(donor_evidence.id)
    corrected_plan = service.current_plan(CASE_ID)
    assert corrected_plan is not None
    service.approve(CASE_ID, approved_by="rehearsal-district-operator")
    service.dispatch(CASE_ID, dispatched_by="rehearsal-panposh-pharmacist")
    chosen = corrected_plan.chosen
    assert chosen is not None
    donor_before = service.repo.canonical_inventory(chosen.donor_id, ITEM_ID).quantity
    recipient_before = service.repo.canonical_inventory(RECIPIENT_ID, ITEM_ID).quantity
    service.verify_source(CASE_ID, observed_quantity=donor_before - chosen.quantity, verified_by="rehearsal-panposh-pharmacist")
    service.verify_destination(CASE_ID, observed_quantity=recipient_before + chosen.quantity, verified_by="rehearsal-lahunipada-pharmacist")
    service.verify_batch(CASE_ID, observed_batch_ids=[a.batch_id for a in chosen.allocations], observed_quantity=chosen.quantity,
                         verified_by="rehearsal-lahunipada-pharmacist")
    _, reconciliation = service.reconcile(CASE_ID)
    exposure = next(iter(service.repo.state().cases[CASE_ID].originally_exposed_refs))
    _, delivery = service.record_care_delivery(CASE_ID, exposure_kind=exposure.kind, exposure_id=exposure.id,
                                               outcome=CareDeliveryOutcome.DELIVERED,
                                               verified_by="rehearsal-lahunipada-pharmacist", source_ref="rehearsal-field/care-delivery/anc-session",
                                               note="Controlled aggregate session delivery observation")
    service.close(CASE_ID, closed_by="rehearsal-district-operator")
    routes = tuple(repo.state().route_observations.values())
    return RehearsalRun(service=service, contract=_contract(service, initial_plan=initial_plan, corrected_plan=corrected_plan,
                                                             initial_evidence=initial_evidence, donor_evidence=donor_evidence,
                                                             reconciliation=reconciliation, delivery=delivery, routes=routes,
                                                             initial_forecast=initial_forecast, initial_impact=initial_impact),
                       route_observations=routes)
