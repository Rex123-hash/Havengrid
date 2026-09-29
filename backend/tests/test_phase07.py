from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from havengrid.api.app import create_app
from havengrid.domain.enums import CareCategory, CaseState, CurrentnessStatus, ExposureKind, CareDeliveryOutcome, Origin, ProvenanceStatus, SourceType
from havengrid.domain.models import CareObligation, ExposureRef, InventoryRecord, Provenance
from havengrid.official.sundargarh import sundargarh_ifa_slice
from havengrid.onboarding.contracts import AuthorityClass, CandidateFactStatus, DiscoveredFact, deterministic_validation
from havengrid.ingest.amb import AMBParseError, load_ifa_red_stock
from havengrid.ingest.activity import ActivityParseError, parse_programme_activity
from havengrid.settings import DataSourceKind, Environment, HavenGridMode, Settings
from havengrid.synthetic.sundargarh import CASE_ID, ITEM, T0


def test_amb_capture_is_district_context_only():
    signals = load_ifa_red_stock("data/raw/official/amb/sundargarh-ifa-stock-2025-2026.json")
    assert len(signals) == 12
    assert signals[0].district_id == "sundargarh"
    assert signals[0].geographic_granularity == "district"
    assert signals[0].source_hash == "5005f5917ea8d399684dfd06b29cb4f2f50d0879297b7b9d6e9bfa5ec0700961"
    assert not isinstance(signals[0], InventoryRecord)
    _, _, official_signals = sundargarh_ifa_slice()
    assert official_signals and all(x.geographic_granularity == "district" for x in official_signals)


def test_amb_schema_rejects_malformed_values():
    import json
    payload = json.loads(open("data/raw/official/amb/sundargarh-ifa-stock-2025-2026.json", encoding="utf-8").read())
    payload["table"]["rows"][0]["values"][0] = "not-a-number"
    with pytest.raises(AMBParseError, match="non-numeric"):
        from havengrid.ingest.amb import parse_ifa_red_stock
        parse_ifa_red_stock(payload)


def test_same_amb_parser_loads_three_odisha_district_captures():
    for district in ("sundargarh", "sambalpur", "kalahandi"):
        signals = load_ifa_red_stock(f"data/raw/official/amb/{district}-ifa-stock-2025-2026.json")
        assert len(signals) == 12 and {s.district_id for s in signals} == {district}
    assert "negative reported value" in load_ifa_red_stock("data/raw/official/amb/kalahandi-ifa-stock-2025-2026.json")[7].provenance.note


def test_typed_exposure_refs_include_obligations_and_unknown_delivery_cannot_close(svc):
    st = svc.repo.state()
    p = Provenance(source_type=SourceType.CARE_SCHEDULE, status=ProvenanceStatus.OBSERVED, observed_at=T0, source_ref="test", origin=Origin.SYNTHETIC_TEST)
    st.care_obligations["ob-test"] = CareObligation(
        id="ob-test", facility_id="bhatpar", category=CareCategory.SCHEDULED, session_at=T0 + timedelta(days=8, hours=3),
        item_id=ITEM, expected_attendance=2, units_per_attendance=1, description="test session", provenance=p,
    )
    case = svc.propose(CASE_ID)
    assert ExposureRef(kind=ExposureKind.CARE_OBLIGATION, id="ob-test") in case.originally_exposed_refs
    forced = case.model_copy(update={"state": CaseState.COVERAGE_RESTORED})
    svc.repo.put_case(forced)
    with pytest.raises(Exception, match="care delivery outcome"):
        svc.close(CASE_ID, closed_by="test")
    svc.record_care_delivery(CASE_ID, exposure_kind=ExposureKind.CARE_OBLIGATION, exposure_id="ob-test", outcome=CareDeliveryOutcome.DELIVERED, verified_by="test", source_ref="register/test")
    assert svc.close(CASE_ID, closed_by="test").state is CaseState.CLOSED


def test_operational_mode_allows_reads_but_blocks_mutations(svc):
    settings = Settings(env=Environment.DEVELOPMENT, data_source=DataSourceKind.OFFICIAL, mode=HavenGridMode.OPERATIONAL)
    client = TestClient(create_app(svc, settings=settings))
    assert client.get("/api/districts/sundargarh/profile").status_code == 200
    assert client.get("/api/districts/sundargarh/stock-signals").status_code == 200
    response = client.post("/api/demo/reset")
    assert response.status_code == 409
    assert response.json()["code"] == "operational_read_only"


def test_programme_activity_grade_requires_explicit_lineage():
    row = {"district_id": "sundargarh", "period": "2025-2026", "indicator": "pregnant women given IFA", "unit": "percent", "evidence_grade": "programme_estimated", "basis": "AMB KPI + 180-day policy", "retrieved_at": "2026-09-11T21:00:00Z", "value": "0.62", "allocation_method": "district aggregate retained", "uncertainty": "0.2", "derived_from": ["amb-kpi:2025-2026"]}
    assert parse_programme_activity(row, source_ref="amb-kpi").evidence_grade.value == "programme_estimated"
    bad = {**row, "allocation_method": None}
    with pytest.raises(ActivityParseError):
        parse_programme_activity(bad, source_ref="amb-kpi")
    unsupported = {k: v for k, v in row.items() if k not in {"value", "allocation_method", "uncertainty", "derived_from"}}
    unsupported["evidence_grade"] = "not_supported"
    assert parse_programme_activity(unsupported, source_ref="amb-kpi").value is None


def test_unverified_facility_cannot_be_operational_donor(svc):
    svc.repo.state().facilities["chc-d"] = svc.repo.state().facilities["chc-d"].model_copy(update={"currentness": CurrentnessStatus.UNVERIFIED})
    case = svc.propose(CASE_ID)
    plan = svc.current_plan(CASE_ID)
    rejected = next(c for c in plan.candidates if c.donor_id == "chc-d")
    assert "FACILITY_UNVERIFIED" in [x.value for x in rejected.rejection_reasons]


def test_district_intelligence_contract_stays_candidate_only_unless_objective_rules_pass():
    fact = DiscoveredFact(field_name="facility.name", candidate_value="CHC Lahunipada", source_url="https://health.odisha.gov.in/x", source_title="official", publisher="Odisha", confidence=Decimal("0.9"), authority_class=AuthorityClass.TRUSTED_GOVERNMENT, district_match=True, retrieved_at=T0)
    assert deterministic_validation(fact).status is CandidateFactStatus.VERIFIED
    unknown = fact.model_copy(update={"district_match": None})
    assert deterministic_validation(unknown).status is CandidateFactStatus.CANDIDATE
