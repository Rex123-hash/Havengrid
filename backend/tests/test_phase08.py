from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest

from havengrid.commands import DEFAULT_CAPABILITY
from havengrid.domain.enums import (CareCategory, CaseAction, CaseState, Origin, ProvenanceStatus,
                                     RouteObservationStatus, SourceQualityFlag, SourceType, CareDeliveryOutcome,
                                     ExposureKind, ReconciliationOutcome, VerificationOutcome)
from havengrid.domain.errors import CommandNotAuthorized, IllegalTransition
from havengrid.domain.models import CareObligation, Coordinate, Provenance, validate_retrieved_at
from havengrid.ingest.google_routes import GoogleRoutesAdapter, load_captured_route_matrix
from havengrid.ingest.amb import load_ifa_red_stock
from havengrid.official.activity import load_sundargarh_kpi_activity
from havengrid.official.facilities import sundargarh_facility_set
from havengrid.rehearsal.sundargarh import CASE_ID, ITEM_ID, RECIPIENT_ID, run_sundargarh_rehearsal
from havengrid.settings import DataSourceKind, Environment, HavenGridMode, Settings
from havengrid.api.app import create_app
from fastapi.testclient import TestClient


def test_operational_page_load_has_zero_commands_and_explicit_command_uses_capability(svc):
    settings = Settings(env=Environment.DEVELOPMENT, data_source=DataSourceKind.OFFICIAL, mode=HavenGridMode.OPERATIONAL)
    client = TestClient(create_app(svc, settings=settings))
    assert client.get("/api/demo/scenario").status_code == 200
    assert client.get("/api/cases/case-bhatpar-amox-001/audit").json() == []
    denied = client.post("/api/cases/case-bhatpar-amox-001/advance", json={"action": "propose"})
    assert denied.status_code == 403 and denied.json()["code"] == "command_not_authorized"
    allowed = client.post("/api/cases/case-bhatpar-amox-001/advance", headers={"X-HavenGrid-Command-Capability": DEFAULT_CAPABILITY}, json={"action": "propose", "actor": "operator"})
    assert allowed.status_code == 200 and allowed.json()["state"] == "INTERVENTION_PROPOSED"
    assert len(client.get("/api/cases/case-bhatpar-amox-001/audit").json()) == 1


def test_operational_reset_is_not_a_command(svc):
    svc.mode = HavenGridMode.OPERATIONAL
    with pytest.raises(IllegalTransition, match="rehearsal-only"):
        svc.reset()
    with pytest.raises(CommandNotAuthorized):
        svc.advance("case-bhatpar-amox-001", CaseAction.PROPOSE, {})
    svc.advance("case-bhatpar-amox-001", CaseAction.PROPOSE, {"actor": "operator"}, capability=DEFAULT_CAPABILITY)


def test_google_routes_success_and_unavailable_are_explicit():
    payload = {"routes": [{"distanceMeters": 16447, "duration": "1919s", "staticDuration": "1919s"}]}
    def transport(_url, _headers, _body):
        return 200, json.dumps(payload).encode()
    adapter = GoogleRoutesAdapter(api_key="test", transport=transport)
    a = Coordinate(latitude=Decimal("21.82004"), longitude=Decimal("84.95452"), source_ref="osm:a", source="osm")
    b = Coordinate(latitude=Decimal("21.8361054"), longitude=Decimal("85.0756074"), source_ref="osm:b", source="osm")
    obs = adapter.compute_route(from_id="sdh-bonai", to_id="chc-lahunipada", origin=a, destination=b, retrieved_at=datetime(2026, 9, 11, 22, tzinfo=timezone.utc))
    assert obs.status is RouteObservationStatus.OK
    assert obs.distance_km == Decimal("16.447") and obs.duration_hours == Decimal("1919") / Decimal("3600")
    assert obs.provenance.origin is Origin.LIVE_EXTERNAL_API and obs.request_hash
    unavailable = GoogleRoutesAdapter().compute_route(from_id="x", to_id="y", origin=a, destination=b)
    assert unavailable.status is RouteObservationStatus.ROUTE_UNAVAILABLE
    assert unavailable.distance_km is None and unavailable.duration_hours is None


def test_captured_routes_have_real_provider_provenance():
    rows = load_captured_route_matrix("data/raw/live/google_routes/sundargarh-lahunipada-matrix.json")
    assert len(rows) == 4 and all(x.status is RouteObservationStatus.OK for x in rows)
    assert all(x.provider == "google_routes" and x.provenance.origin is Origin.LIVE_EXTERNAL_API for x in rows)
    assert rows[0].distance_km != Decimal("42") and rows[0].duration_hours != Decimal("1.5")


def test_ifa_rules_are_separate_antenatal_and_postpartum():
    from havengrid.official.sundargarh import ifa_red_item
    item = ifa_red_item()
    assert [x.id for x in item.dose_rules] == ["ifa-red-antenatal", "ifa-red-postpartum"]
    assert item.dose_rules[0].duration_days == 180 and "fourth month" in item.dose_rules[0].programme_phase
    assert item.dose_rules[1].duration_days == 180 and "postpartum" in item.dose_rules[1].programme_phase


def test_rehearsal_contract_is_consistent_and_care_recovery_is_separate():
    run = run_sundargarh_rehearsal()
    contract = run.contract
    assert run.service.repo.case(CASE_ID).state is CaseState.CLOSED
    assert contract.recipient_facility["id"] == RECIPIENT_ID
    assert contract.initial_chosen_donor == "sdh-bonai"
    assert contract.replanned_donor == "sdh-panposh"
    assert contract.transfer_quantity == 47
    assert contract.coverage_breach_day == 5 and contract.stockout_day == 8
    assert contract.exposure_range.low == 11 and contract.exposure_range.high == 15
    assert contract.programme_obligation["numeric_basis_origin"] == "REHEARSAL_ASSUMPTION"
    assert contract.programme_obligation["public_programme_basis"] == "AMB"
    assert contract.programme_obligation["facility_denominator_status"] == "UNKNOWN"
    assert contract.transfer_quantity_unit == "tablet" and contract.physical_dispatch_unit == "UNKNOWN"
    methods = contract.programme_obligation["allocation_method_comparison"]
    assert len(methods) == 2 and methods[0]["used"] and methods[1]["result"] == "UNKNOWN"
    assert "individual" not in contract.programme_obligation["uncertainty"].lower()
    assert contract.programme_obligation["estimated_population"] == {"low": 11, "high": 15}
    assert contract.fact_classifications["baseline_demand"].value == "REHEARSAL_ASSUMPTION"
    assert contract.fact_classifications["forecast"].value == "MODEL_DERIVED"
    assert {x.value for x in contract.fact_classifications.values()} <= {
        "REAL_PUBLIC", "LIVE_EXTERNAL_API", "REHEARSAL_EVIDENCE", "REHEARSAL_ASSUMPTION", "MODEL_DERIVED", "UNKNOWN"
    }
    assert contract.derived_from["forecast"] and contract.assumption_notes["baseline_demand"]
    assert contract.coverage_recovery["status"] == "coverage_restored"
    assert contract.coverage_recovery["reconciliation_protected_count"] == 0
    assert contract.coverage_recovery["protected_count"] == 1
    assert contract.coverage_recovery["status"] != contract.care_delivery_verification["outcome"]
    assert contract.care_delivery_verification["outcome"] == "delivered"
    assert "patient" in " ".join(contract.unknown_facts) or contract.programme_obligation["evidence_grade"] == "programme_estimated"


def test_amb_negative_values_are_preserved_and_flagged():
    from havengrid.ingest.amb import load_ifa_red_stock
    rows = load_ifa_red_stock("data/raw/official/amb/kalahandi-ifa-stock-2025-2026.json")
    assert rows[6].available == Decimal("-752000")
    assert SourceQualityFlag.NEGATIVE_REPORTED_STOCK in rows[6].provenance.quality_flags
    assert SourceQualityFlag.NEGATIVE_REPORTED_STOCK in rows[6].quality_flags


def test_rehearsal_donor_ranking_exposes_route_facts():
    run = run_sundargarh_rehearsal()
    candidates = run.contract.initial_donor_candidates
    assert [x.donor_id for x in candidates[:2]] == ["sdh-bonai", "sdh-panposh"]
    assert candidates[0].route is not None and candidates[1].route is not None
    assert candidates[0].route.distance_km < candidates[1].route.distance_km


def test_readiness_and_stock_quality_are_inspectable_over_api():
    from havengrid.rehearsal.sundargarh import build_sundargarh_rehearsal
    from havengrid.store import InMemoryRepository
    from havengrid.service import HavenGridService
    repo = InMemoryRepository(build_sundargarh_rehearsal)
    client = TestClient(create_app(HavenGridService(repo), settings=Settings(env=Environment.DEVELOPMENT, data_source=DataSourceKind.OFFICIAL, mode=HavenGridMode.REHEARSAL)))
    readiness = client.get("/api/districts/sundargarh/readiness").json()
    assert readiness["facility_inventory"] == "partial" and readiness["routes"] == "ready"
    stock = client.get("/api/districts/sundargarh/stock-signals").json()
    assert "quality_flags" in stock[0] and "quality_flags" in stock[0]["provenance"]


def test_same_kernel_portability_smoke_for_sambalpur_and_kalahandi():
    from havengrid.rehearsal.sundargarh import build_sundargarh_rehearsal
    from havengrid.store import InMemoryRepository
    from havengrid.service import HavenGridService
    from havengrid.profiles import portability_profiles
    for district_id in ("sambalpur", "kalahandi"):
        rows = load_ifa_red_stock(f"data/raw/official/amb/{district_id}-ifa-stock-2025-2026.json")
        assert rows and rows[0].district_id == district_id
        repo = InMemoryRepository(build_sundargarh_rehearsal)
        repo.state().district = repo.state().district.model_copy(update={"id": district_id, "name": district_id.title()})
        repo.state().district_profile = next(p for p in portability_profiles() if p.id == district_id)
        assert HavenGridService(repo).forecast("sdh-panposh", ITEM_ID).status.value == "forecast"


def test_future_retrieval_timestamp_is_rejected_beyond_clock_skew():
    trusted = datetime(2026, 9, 11, 22, 0, tzinfo=timezone.utc)
    assert validate_retrieved_at(trusted + timedelta(minutes=4), now=trusted) == trusted + timedelta(minutes=4)
    with pytest.raises(ValueError, match="ahead of trusted clock"):
        validate_retrieved_at(trusted + timedelta(minutes=6), now=trusted)


def test_captured_retrieval_timestamps_are_temporally_possible():
    trusted = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert all(x.retrieved_at <= trusted for x in load_ifa_red_stock("data/raw/official/amb/sundargarh-ifa-stock-2025-2026.json"))
    assert all(x.provenance.retrieved_at <= trusted for x in load_sundargarh_kpi_activity())
    assert all(x.retrieved_at <= trusted for x in load_captured_route_matrix("data/raw/live/google_routes/sundargarh-lahunipada-matrix.json"))
    assert all(x.coordinate_provenance is None or x.coordinate_provenance.retrieved_at is None or x.coordinate_provenance.retrieved_at <= trusted for x in sundargarh_facility_set())


def test_obligation_reconcile_restores_coverage_before_care_protection(svc, case_id, item_id):
    from tests.conftest import run_to_batch_matched
    p = Provenance(source_type=SourceType.CARE_SCHEDULE, status=ProvenanceStatus.OBSERVED,
                   observed_at=svc.now(), source_ref="rehearsal/obligation", origin=Origin.SYNTHETIC_TEST)
    svc.repo.state().care_obligations["obligation-gate"] = CareObligation(
        id="obligation-gate", facility_id="bhatpar", category=CareCategory.MATERNAL,
        session_at=svc.repo.state().district.day_start(9), item_id=item_id,
        expected_attendance=2, units_per_attendance=1, description="aggregate test obligation", provenance=p)
    run_to_batch_matched(svc)
    case, rec = svc.reconcile(case_id)
    assert rec.outcome is ReconciliationOutcome.COVERAGE_RESTORED
    assert rec.coverage_status.value == "coverage_restored"
    assert rec.protected_count == 0 and case.state is CaseState.COVERAGE_RESTORED
    with pytest.raises(IllegalTransition):
        svc.close(case_id, closed_by="tester")
    for outcome in (CareDeliveryOutcome.UNKNOWN, CareDeliveryOutcome.NOT_DELIVERED, CareDeliveryOutcome.DEFERRED):
        case, _ = svc.record_care_delivery(case_id, exposure_kind=ExposureKind.CARE_OBLIGATION,
                                            exposure_id="obligation-gate", outcome=outcome,
                                            verified_by="tester", source_ref="rehearsal/test")
        assert case.state is CaseState.COVERAGE_RESTORED
    case, _ = svc.record_care_delivery(case_id, exposure_kind=ExposureKind.CARE_OBLIGATION,
                                       exposure_id="obligation-gate", outcome=CareDeliveryOutcome.DELIVERED,
                                       verified_by="tester", source_ref="rehearsal/test")
    assert case.state is CaseState.CARE_PROTECTED
    assert svc.close(case_id, closed_by="tester").state is CaseState.CLOSED
