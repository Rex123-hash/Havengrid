"""Small, source-backed Sundargarh facility roster for onboarding.

This is metadata only. It intentionally carries no stock, batch, route, or
care activity facts; those families have separate source adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from ..domain.enums import CurrentnessStatus, FacilityTier, Origin, ProvenanceStatus, SourceType
from ..domain.models import Facility, Provenance, SchematicPosition

FACILITY_SOURCE = "https://health.odisha.gov.in/or/healthinstitutes/parathama-raepharaala-yaunaita"
SOURCE_DATE = datetime(2026, 6, 13, tzinfo=timezone.utc)
# Preserve the originally recorded time for audit; its retrieval timing is
# unverified. No raw capture proves a corrected UTC instant.
COORDINATE_RECORDED_AT = datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc)

_COORDINATES: dict[str, tuple[str, str, str]] = {
    "dhh-sundargarh": ("22.1184085", "84.0362638", "https://www.openstreetmap.org/node/7208764204"),
    "sdh-bonai": ("21.82004", "84.95452", "https://www.openstreetmap.org/node/566196813"),
    "sdh-panposh": ("22.2295801", "84.8044922", "https://www.openstreetmap.org/node/7081521265"),
    "chc-lahunipada": ("21.8361054", "85.0756074", "https://www.openstreetmap.org/node/10100695"),
    "chc-laing": ("22.2392629", "84.6536373", "https://www.openstreetmap.org/node/7222905371"),
    "chc-mangaspur": ("21.9518497", "83.9901732", "https://www.openstreetmap.org/node/1460229008"),
}


def _coordinate_provenance(ref: str) -> Provenance:
    return Provenance(source_type=SourceType.FACILITY_DIRECTORY, status=ProvenanceStatus.OBSERVED,
                      observed_at=COORDINATE_RECORDED_AT, source_ref=ref, origin=Origin.LIVE_EXTERNAL_API,
                      publisher="OpenStreetMap contributors", retrieved_at=None,
                      geographic_granularity="point", note="Coordinate retrieval time UNKNOWN. Originally recorded 2026-09-12T00:00:00Z was ahead of audit clock; retained as unverified metadata, not an accepted retrieval instant. Corroborating OSM point; official identity comes from Odisha.")


def sundargarh_facility_set() -> tuple[Facility, ...]:
    rows = (
        ("dhh-sundargarh", "District Headquarters Hospital Sundargarh", "DHH Sundargarh", FacilityTier.WAREHOUSE, "Sundargarh", CurrentnessStatus.CURRENT_VERIFIED),
        ("sdh-bonai", "Sub-Divisional Hospital Bonai", "SDH Bonai", FacilityTier.CHC, "Bonai", CurrentnessStatus.CURRENT_VERIFIED),
        ("sdh-panposh", "Sub-Divisional Hospital Panposh", "SDH Panposh", FacilityTier.CHC, "Panposh", CurrentnessStatus.CURRENT_VERIFIED),
        ("chc-lahunipada", "Community Health Centre Lahunipada", "CHC Lahunipada", FacilityTier.CHC, "Lahunipada", CurrentnessStatus.CURRENT_VERIFIED),
        ("chc-sargipali", "Community Health Centre Sargipali", "CHC Sargipali", FacilityTier.CHC, "Tangarpali", CurrentnessStatus.CURRENT_VERIFIED),
        ("chc-laing", "Community Health Centre Laing", "CHC Laing", FacilityTier.CHC, "Kutra", CurrentnessStatus.HISTORICAL_CORROBORATED),
        ("chc-mangaspur", "Community Health Centre Mangaspur", "CHC Mangaspur", FacilityTier.CHC, "Gurundia", CurrentnessStatus.HISTORICAL_CORROBORATED),
    )
    out: list[Facility] = []
    for id_, name, short, tier, block, currentness in rows:
        lat_lon_ref = _COORDINATES.get(id_)
        lat = Decimal(lat_lon_ref[0]) if lat_lon_ref else None
        lon = Decimal(lat_lon_ref[1]) if lat_lon_ref else None
        coord_prov = _coordinate_provenance(lat_lon_ref[2]) if lat_lon_ref else None
        out.append(Facility(id=id_, name=name, short_name=short, tier=tier, district_id="sundargarh", block=block,
                            facility_type="DHH" if id_ == "dhh-sundargarh" else tier.value.upper(), position=SchematicPosition(x=0, y=0),
                            source_ref=FACILITY_SOURCE, source_date=SOURCE_DATE, currentness=currentness,
                            coordinate_source="osm_corroborated" if lat_lon_ref else "not_captured_from_source",
                            latitude=lat, longitude=lon, coordinate_provenance=coord_prov))
    return tuple(out)
