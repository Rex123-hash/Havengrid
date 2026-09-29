from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from havengrid.domain.enums import Origin, ProvenanceStatus, SourceType
from havengrid.domain.models import DemandProfile, Facility, InventoryRecord, Provenance, SchematicPosition
from havengrid.domain.enums import FacilityTier


def prov(**kw):
    base = dict(source_type=SourceType.DIGITAL_LEDGER, status=ProvenanceStatus.REPORTED, observed_at=datetime(2026, 9, 14, tzinfo=timezone.utc), source_ref="x", origin=Origin.SYNTHETIC_TEST)
    base.update(kw)
    return Provenance(**base)


def test_provenance_requires_timezone_aware():
    with pytest.raises(ValidationError):
        prov(observed_at=datetime(2026, 9, 14))


def test_provenance_carries_origin_and_confidence_bounds():
    p = prov(confidence=Decimal("0.83"))
    assert p.origin is Origin.SYNTHETIC_TEST
    with pytest.raises(ValidationError):
        prov(confidence=Decimal("1.2"))


def test_inventory_quantity_non_negative():
    with pytest.raises(ValidationError):
        InventoryRecord(id="i", facility_id="bhatpar", item_id="amx", quantity=-1, provenance=prov(), canonical=True)


def test_demand_profile_rejects_empty_or_negative():
    with pytest.raises(ValidationError):
        DemandProfile(facility_id="a", item_id="b", daily=(), shape_note="", provenance=prov())
    with pytest.raises(ValidationError):
        DemandProfile(facility_id="a", item_id="b", daily=(1, -2), shape_note="", provenance=prov())


def test_ids_are_constrained():
    with pytest.raises(ValidationError):
        Facility(id="Bad Id", name="n", short_name="s", tier=FacilityTier.PHC, district_id="d", position=SchematicPosition(x=0, y=0))


def test_models_are_frozen():
    f = Facility(id="ok", name="n", short_name="s", tier=FacilityTier.PHC, district_id="d", position=SchematicPosition(x=0, y=0))
    with pytest.raises(ValidationError):
        f.name = "changed"  # type: ignore[misc]
