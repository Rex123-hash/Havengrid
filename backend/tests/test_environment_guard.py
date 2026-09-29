"""Synthetic data may test HAVEN GRID. It must not pretend to be the world HAVEN GRID observes."""

import pytest
from fastapi.testclient import TestClient

from havengrid.api.app import create_app
from havengrid.bootstrap import bootstrap
from havengrid.domain.enums import Origin
from havengrid.settings import DataSourceKind, Environment, EnvironmentIntegrityError, Settings, validate


def S(env, source, uri=None):
    return Settings(env=Environment(env), data_source=DataSourceKind(source), official_source_uri=uri)


@pytest.mark.parametrize("env", ["development", "test"])
def test_synthetic_permitted_in_dev_and_test(env):
    b = bootstrap(S(env, "synthetic"))
    assert not b.degraded and b.source_origin == "synthetic_test"
    assert b.service.actor_origin is Origin.SYNTHETIC_TEST


@pytest.mark.parametrize("env", ["staging", "judge", "production"])
def test_synthetic_forbidden_outside_dev_and_test(env):
    with pytest.raises(EnvironmentIntegrityError):
        validate(S(env, "synthetic"))
    with pytest.raises(EnvironmentIntegrityError):
        bootstrap(S(env, "synthetic"))
    with pytest.raises(EnvironmentIntegrityError):
        create_app(settings=S(env, "synthetic"))   # the process must not start


@pytest.mark.parametrize("env", ["staging", "judge", "production"])
def test_no_source_is_degraded_not_synthetic(env):
    b = bootstrap(S(env, "none"))
    assert b.degraded and "no data source configured" in b.degraded_reason
    client = TestClient(create_app(settings=S(env, "none")))
    h = client.get("/health").json()
    assert h["status"] == "degraded" and h["environment"] == env
    for path in ("/api/demo/scenario", "/api/districts/sundargarh/network", "/api/facilities/bhatpar", "/api/cases/x"):
        r = client.get(path)
        assert r.status_code == 503, path
        assert r.json()["code"] == "data_source_unavailable"
    # nothing synthetic leaked anywhere in the degraded payloads
    assert "191" not in client.get("/api/demo/scenario").text and "bhatpar" not in client.get("/api/demo/scenario").text.lower().replace("/api/", "")


def test_official_source_without_adapter_is_degraded_with_reason():
    b = bootstrap(S("production", "official", uri="hmis://sundargarh"))
    assert b.degraded and "no official data-source adapter" in b.degraded_reason
    assert b.source_id == "hmis://sundargarh" and b.source_origin == "official_system_export"


def test_defaults_from_environment_variables():
    assert Settings.from_env({}).env is Environment.DEVELOPMENT
    assert Settings.from_env({}).data_source is DataSourceKind.REHEARSAL
    prod = Settings.from_env({"HAVENGRID_ENV": "production"})
    assert prod.data_source is DataSourceKind.NONE           # never defaults to synthetic
    assert Settings.from_env({"HAVENGRID_ENV": "judge"}).actor_origin is Origin.USER_SUPPLIED_EVIDENCE


def test_health_and_bundle_declare_origins_honestly():
    client = TestClient(create_app(settings=S("development", "synthetic")))
    h = client.get("/health").json()
    assert h["synthetic"] is True and h["origins"] == ["synthetic_test"] and h["data_source"] == "synthetic/sundargarh"
    b = client.get("/api/demo/scenario").json()
    assert b["synthetic"] is True and b["data_origin"]["origins"] == ["synthetic_test"] and b["data_origin"]["environment"] == "development"


def test_actor_origin_flows_into_confirmed_records():
    from decimal import Decimal
    from havengrid.ingest.assembler import assemble
    from havengrid.ingest.synthetic_source import SyntheticSundargarhSource
    from havengrid.service import HavenGridService
    from havengrid.store import InMemoryRepository
    # Same fixture, but pretend the deployment's humans are real: their records must not be stamped synthetic.
    svc = HavenGridService(InMemoryRepository(lambda: assemble(SyntheticSundargarhSource(), open_case=("case-bhatpar-amox-001", "bhatpar", "amoxicillin-susp-125"))),
                           actor_origin=Origin.USER_SUPPLIED_EVIDENCE)
    case_id = "case-bhatpar-amox-001"
    svc.propose(case_id)
    _, ev = svc.submit_evidence(case_id, facility_id="chc-d", observed_quantity=126, confidence=Decimal("0.83"), captured_via="photo")
    svc.confirm_evidence(case_id, ev.id, confirmed_by="pharmacist")
    new = svc.repo.canonical_inventory("chc-d", "amoxicillin-susp-125")
    assert new.provenance.origin is Origin.USER_SUPPLIED_EVIDENCE
    old = svc.repo.inventory_lineage("chc-d", "amoxicillin-susp-125")[0]
    assert old.provenance.origin is Origin.SYNTHETIC_TEST     # the inherited fact keeps its own origin
    assert svc.data_origins() == ["synthetic_test", "user_supplied_evidence"]
