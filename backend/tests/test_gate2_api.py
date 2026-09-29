"""The default HTTP app serves the interactive IFA checkpoint without replaying it."""

from copy import deepcopy

from fastapi.testclient import TestClient

from havengrid.api.app import create_app
from havengrid.api.schemas import WorkspaceSnapshotOut
from havengrid.rehearsal.sundargarh import CASE_ID, ITEM_ID, RECIPIENT_ID
from havengrid.settings import DataSourceKind, Environment, Settings


def current_client() -> TestClient:
    return TestClient(create_app(settings=Settings(env=Environment.DEVELOPMENT, data_source=DataSourceKind.REHEARSAL)))


def test_default_runtime_selects_current_rehearsal_and_historical_remains_explicit():
    default = TestClient(create_app())
    assert default.get("/health").json()["data_source"] == "rehearsal/sundargarh-ifa-red"
    assert default.get("/api/demo/scenario").json()["item"]["id"] == ITEM_ID

    historical = TestClient(create_app(settings=Settings(env=Environment.TEST, data_source=DataSourceKind.SYNTHETIC)))
    old = historical.get("/api/demo/scenario").json()
    assert old["item"]["id"] == "amoxicillin-susp-125"
    assert old["case"]["id"] == "case-bhatpar-amox-001"


def test_current_http_reads_agree_at_pre_correction_checkpoint():
    client = current_client()
    health = client.get("/health").json()
    bundle = client.get("/api/demo/scenario").json()
    profile = client.get("/api/districts/sundargarh/profile").json()
    stock = client.get("/api/districts/sundargarh/stock-signals").json()
    network = client.get("/api/districts/sundargarh/network").json()
    forecast = client.get("/api/districts/sundargarh/forecast").json()
    facility = client.get(f"/api/facilities/{RECIPIENT_ID}").json()
    impact = client.get(f"/api/facilities/{RECIPIENT_ID}/care-impact").json()
    case = client.get(f"/api/cases/{CASE_ID}").json()
    plans = client.get(f"/api/cases/{CASE_ID}/interventions").json()
    audit = client.get(f"/api/cases/{CASE_ID}/audit").json()
    response = client.get("/api/districts/sundargarh/workspace")
    assert response.status_code == 200
    workspace = response.json()
    assert WorkspaceSnapshotOut.model_validate(workspace).active_case.id == CASE_ID

    assert health["status"] == "ok" and health["mode"] == "rehearsal"
    assert profile["id"] == network["district"]["id"] == workspace["metadata"]["district"]["id"] == "sundargarh"
    assert bundle["item"]["id"] == network["item"]["id"] == facility["forecast"]["item_id"] == workspace["metadata"]["commodity"]["id"] == ITEM_ID
    assert all(x["item_id"] == ITEM_ID for x in forecast.values())
    assert all(x["item_id"] == ITEM_ID for x in stock)
    assert stock and all(x["geographic_granularity"] == "district" for x in stock)
    assert bundle["focus_facility_id"] == case["recipient_id"] == workspace["active_case"]["recipient_id"] == RECIPIENT_ID
    assert case["id"] == workspace["active_case"]["id"] == CASE_ID
    assert case["state"] == bundle["case"]["state"] == workspace["recovery"]["state"] == "AWAITING_EVIDENCE_CONFIRMATION"
    assert workspace["recovery"]["domain_legal_actions"] == ["confirm_evidence", "reject_evidence"]
    assert workspace["recovery"]["authorization_status"] == "not_evaluated"
    assert workspace["metadata"]["designation"] == "controlled_rehearsal"

    assert facility["canonical_inventory"]["quantity"] == forecast[RECIPIENT_ID]["starting_inventory"] == 30
    assert impact["status"] == "forecast" and impact["exposed_total"] == 13
    assert forecast[RECIPIENT_ID]["coverage_breach_day"] == 5
    assert forecast[RECIPIENT_ID]["stockout_day"] == 8
    assert forecast[RECIPIENT_ID]["projected_demand_window"] == 69
    assert bundle["plan"]["id"] == plans[-1]["id"] == workspace["current_plan"]["id"]
    assert plans[-1]["chosen_donor_id"] == "sdh-bonai"
    assert next(x for x in plans[-1]["candidates"] if x["donor_id"] == "sdh-bonai")["quantity"] == 47
    assert not plans[-1]["invalidated"] and workspace["previous_plans"] == []
    assert workspace["intelligence"]["care_obligations"][0]["facility_denominator_status"] == "UNKNOWN"
    assert workspace["metadata"]["commodity"]["physical_dispatch_unit"] == "UNKNOWN"

    bonai = next(x for x in workspace["evidence"] if x["evidence"]["facility_id"] == "sdh-bonai")
    assert bonai["evidence"]["observed_quantity"] == 20
    assert bonai["evidence"]["canonical_quantity_at_submission"] == bonai["current_canonical_quantity"] == 120
    assert bonai["evidence"]["state"] == "awaiting_confirmation"
    assert bonai["evidence"]["evidence_class"] == "REHEARSAL_FIELD_OBSERVATION"
    assert audit[-1]["action"] == "submit_evidence"
    assert workspace["network"]["facilities"] and workspace["intelligence"]["stock_signals"]
    assert any(x["forecast"]["status"] == "unavailable" and x["canonical_inventory"] is None
               and x["care_impact"]["exposed_total"] is None for x in workspace["network"]["facilities"])
    assert client.get("/api/districts/not-real/workspace").status_code == 404


def test_http_confirmation_runs_real_invalidation_and_replan():
    client = current_client()
    before = client.get("/api/districts/sundargarh/workspace").json()
    pending = next(x["evidence"] for x in before["evidence"] if x["evidence"]["facility_id"] == "sdh-bonai")
    response = client.post(f"/api/cases/{CASE_ID}/evidence/{pending['id']}/confirm",
                           json={"actor": "rehearsal-pharmacist", "note": "confirmed shelf count"})
    assert response.status_code == 200 and response.json()["state"] == "PLAN_RECALCULATED"
    after = client.get("/api/districts/sundargarh/workspace").json()
    assert after["active_case"]["state"] == "PLAN_RECALCULATED"
    assert after["previous_plans"][0]["id"] == before["current_plan"]["id"]
    assert after["previous_plans"][0]["invalidated"] is True
    assert after["current_plan"]["chosen_donor_id"] == "sdh-panposh"
    assert after["current_plan"]["id"] != before["current_plan"]["id"]
    bonai = next(x for x in after["network"]["facilities"] if x["facility"]["id"] == "sdh-bonai")
    assert bonai["canonical_inventory"]["quantity"] == 20
    assert bonai["canonical_inventory"]["provenance"]["source_ref"] == f"evidence/{pending['id']}"
    assert next(x for x in after["evidence"] if x["evidence"]["id"] == pending["id"])["evidence"]["state"] == "confirmed"
    assert set(after["recovery"]["domain_legal_actions"]) == {"approve", "submit_evidence"}


def test_startup_and_repeated_reads_do_not_replay_or_mutate():
    client = current_client()
    service = client.app.state.service
    before = deepcopy(service.repo.state())
    tick = service._tick
    paths = ("/health", "/api/demo/scenario", "/api/districts/sundargarh/workspace",
             f"/api/cases/{CASE_ID}", "/api/districts/sundargarh/network",
             f"/api/facilities/{RECIPIENT_ID}/care-impact")
    for _ in range(3):
        for path in paths:
            assert client.get(path).status_code == 200, path
    assert service.repo.state() == before and service._tick == tick
    assert service.repo.case(CASE_ID).state.value == "AWAITING_EVIDENCE_CONFIRMATION"
    assert not service.repo.state().verifications and not service.repo.state().reconciliations


def test_explicit_rehearsal_reset_restores_the_same_checkpoint_and_clock():
    client = current_client()
    initial = client.get("/api/districts/sundargarh/workspace").json()
    pending = next(x["evidence"] for x in initial["evidence"] if x["evidence"]["facility_id"] == "sdh-bonai")
    assert client.post(f"/api/cases/{CASE_ID}/evidence/{pending['id']}/confirm", json={"actor": "tester"}).status_code == 200
    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200 and reset.json()["state"] == "AWAITING_EVIDENCE_CONFIRMATION"
    restored = client.get("/api/districts/sundargarh/workspace").json()
    assert restored == initial
