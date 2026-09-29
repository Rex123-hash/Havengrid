from tests.conftest import run_to_batch_matched


def test_health_declares_synthetic(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["synthetic"] is True


def test_scenario_bundle_shape_and_values(client):
    r = client.get("/api/demo/scenario")
    assert r.status_code == 200
    j = r.json()
    assert j["synthetic"] is True
    assert len(j["facilities"]) == 14 and len(j["links"]) == 14
    f = j["forecasts"]["bhatpar"]
    assert f["coverage_breach_day"] == 8 and f["stockout_day"] == 11
    assert f["projected_demand_window"] == 191 and f["gap_window"] == 48
    assert j["forecasts"]["kutra"]["status"] == "unavailable"
    ci = j["care_impacts"]["bhatpar"]
    assert ci["scheduled_in_window"] == 23 and ci["exposed_total"] == 13 and ci["unserved_total"] == 6
    assert ci["exposed_by_category"] == {"paediatric": 7, "maternal": 4, "scheduled": 2}
    assert len(j["focus_care_events"]) == 23 and sum(e["exposed"] for e in j["focus_care_events"]) == 13
    assert j["case"]["state"] == "FORECASTED" and j["plan"] is None


def test_network_and_forecast_endpoints(client):
    assert client.get("/api/districts/sundargarh/network").status_code == 200
    assert client.get("/api/districts/nowhere/network").status_code == 404
    r = client.get("/api/districts/sundargarh/forecast", params={"horizon_days": 7})
    assert r.status_code == 200
    assert r.json()["bhatpar"]["coverage_breach_day"] is None       # day 8 is beyond a 7-day horizon
    assert r.json()["kansbahal"]["coverage_breach_day"] == 7
    assert len(r.json()["bhatpar"]["projection"]) == 7


def test_facility_detail_and_care_impact(client):
    r = client.get("/api/facilities/bhatpar")
    assert r.status_code == 200
    j = r.json()
    assert j["canonical_inventory"]["quantity"] == 143 and j["days_since_physical_count"] == 3
    assert j["care_impact"]["exposed_total"] == 13
    assert client.get("/api/facilities/nope").status_code == 404
    assert client.get("/api/facilities/chc-d/care-impact").json()["exposed_total"] == 0


def test_full_story_over_http(client, case_id):
    def adv(action, **kw):
        return client.post(f"/api/cases/{case_id}/advance", json={"action": action, **kw})

    assert adv("propose").json()["state"] == "INTERVENTION_PROPOSED"
    plans = client.get(f"/api/cases/{case_id}/interventions").json()
    assert plans[-1]["chosen_donor_id"] == "chc-d"
    chc_d = next(c for c in plans[-1]["candidates"] if c["donor_id"] == "chc-d")
    assert chc_d["allocations"] == [{"batch_id": "AMX-2401-K", "quantity": 80, "expires_at": "2026-10-04T02:30:00Z"}]
    kans = next(c for c in plans[-1]["candidates"] if c["donor_id"] == "kansbahal")
    assert kans["rejection_reasons"] == ["DONOR_ALREADY_AT_RISK"] and kans["explanations"]

    ev = client.post(f"/api/cases/{case_id}/evidence", json={"facility_id": "chc-d", "observed_quantity": 126, "confidence": "0.83"})
    assert ev.status_code == 201 and ev.json()["state"] == "awaiting_confirmation"
    assert client.get("/api/facilities/chc-d").json()["canonical_inventory"]["quantity"] == 286

    r = client.post(f"/api/cases/{case_id}/evidence/{ev.json()['id']}/confirm", json={"actor": "district-pharmacist"})
    assert r.status_code == 200 and r.json()["state"] == "PLAN_RECALCULATED"
    assert client.get("/api/facilities/chc-d").json()["canonical_inventory"]["quantity"] == 126
    plans = client.get(f"/api/cases/{case_id}/interventions").json()
    assert [p["chosen_donor_id"] for p in plans] == ["chc-d", "chc-b"] and plans[0]["invalidated"]

    assert adv("approve").json()["state"] == "APPROVED"
    assert adv("dispatch").json()["state"] == "DISPATCHED"
    assert adv("verify_source", observed_quantity=None).json()["state"] == "DISPATCHED"          # UNKNOWN does not advance
    assert adv("verify_source", observed_quantity=260).json()["state"] == "SOURCE_VERIFIED"
    assert adv("verify_destination", observed_quantity=223).json()["state"] == "DESTINATION_VERIFIED"
    assert adv("verify_batch", observed_batch_ids=["AMX-2403-B"], observed_quantity=80).json()["state"] == "BATCH_MATCHED"
    assert adv("close").status_code == 409                                                          # cannot skip reconcile
    r = adv("reconcile")
    assert r.json()["state"] == "CARE_PROTECTED" and r.json()["care_protected_count"] == 13
    assert adv("close").json()["state"] == "CLOSED"

    bundle = client.get("/api/demo/scenario").json()
    assert bundle["reconciliations"][-1]["outcome"] == "care_protected"
    assert [v["outcome"] for v in bundle["verifications"]] == ["unknown", "verified", "verified", "verified"]
    assert len(client.get(f"/api/cases/{case_id}/audit").json()) > 10


def test_api_rejects_system_actions_and_asserted_outcomes(client, case_id, svc):
    run_to_batch_matched(svc)
    assert client.post(f"/api/cases/{case_id}/advance", json={"action": "invalidate_plan"}).status_code == 409
    assert client.post(f"/api/cases/{case_id}/advance", json={"action": "submit_evidence"}).status_code == 422
    # extra="forbid" on the request schema: an asserted outcome cannot even be expressed
    assert client.post(f"/api/cases/{case_id}/advance", json={"action": "reconcile", "care_protected": True}).status_code == 422


def test_reset_restores_original_state(client, case_id):
    client.post(f"/api/cases/{case_id}/advance", json={"action": "propose"})
    r = client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["state"] == "FORECASTED"
    j = client.get("/api/demo/scenario").json()
    assert j["plan"] is None and j["evidence"] == [] and j["forecasts"]["chc-d"]["starting_inventory"] == 286


def test_error_envelope(client):
    r = client.get("/api/cases/missing")
    assert r.status_code == 404 and r.json()["code"] == "not_found"


def test_command_id_makes_replay_commands_idempotent_over_http(client, case_id):
    """The frontend replay tags every command with a run-scoped command_id so a
    duplicated POST (retry, double effect) is acknowledged, not re-applied."""
    body = {"action": "propose", "command_id": "run-1:propose"}
    a = client.post(f"/api/cases/{case_id}/advance", json=body)
    b = client.post(f"/api/cases/{case_id}/advance", json=body)
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["state"] == b.json()["state"] == "INTERVENTION_PROPOSED"
    assert len([x for x in client.get(f"/api/cases/{case_id}/audit").json() if x["action"] == "propose"]) == 1
    # a genuinely different command in the wrong state still fails — idempotency is not leniency
    assert client.post(f"/api/cases/{case_id}/advance", json={"action": "propose", "command_id": "run-2:propose"}).status_code == 409


def test_reset_returns_the_case_id_the_frontend_discovers(client):
    r = client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["id"] == "case-bhatpar-amox-001"
