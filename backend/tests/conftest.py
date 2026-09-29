from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from havengrid.api.app import create_app
from havengrid.synthetic.sundargarh import CASE_ID, ITEM, T0, build_sundargarh
from havengrid.service import HavenGridService
from havengrid.store import InMemoryRepository


@pytest.fixture
def svc() -> HavenGridService:
    return HavenGridService(InMemoryRepository(build_sundargarh))


@pytest.fixture
def client(svc) -> TestClient:
    return TestClient(create_app(svc))


@pytest.fixture
def case_id() -> str:
    return CASE_ID


@pytest.fixture
def item_id() -> str:
    return ITEM


@pytest.fixture
def t0():
    return T0


@pytest.fixture
def d083() -> Decimal:
    return Decimal("0.83")


def run_to_proposed(svc):
    return svc.propose(CASE_ID)


def run_to_recalculated(svc, confidence=Decimal("0.83")):
    svc.propose(CASE_ID)
    _, ev = svc.submit_evidence(CASE_ID, facility_id="chc-d", observed_quantity=126, confidence=confidence, captured_via="field photograph")
    return svc.confirm_evidence(CASE_ID, ev.id, confirmed_by="district-pharmacist"), ev


def run_to_batch_matched(svc):
    case, ev = run_to_recalculated(svc)
    svc.approve(CASE_ID, approved_by="dmo")
    svc.dispatch(CASE_ID, dispatched_by="chc-b")
    svc.verify_source(CASE_ID, observed_quantity=260, verified_by="chc-b")
    svc.verify_destination(CASE_ID, observed_quantity=223, verified_by="bhatpar")
    case, _ = svc.verify_batch(CASE_ID, observed_batch_ids=["AMX-2403-B"], observed_quantity=80, verified_by="bhatpar")
    return case
