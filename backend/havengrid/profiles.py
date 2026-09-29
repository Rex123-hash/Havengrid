"""District profile configuration for the first official-data vertical slice.

Profiles only describe source seams and policy references. They do not turn
district aggregates into facility inventory and they do not invent a facility
roster when an official source is unavailable.
"""

from __future__ import annotations

from .domain.enums import CurrentnessStatus, Origin
from .domain.models import DistrictProfile, SourceCatalogEntry


def _source(id: str, family: str, title: str, uri: str, *, origin: Origin, currentness: CurrentnessStatus = CurrentnessStatus.UNKNOWN, notes: str = "", publisher: str = "Government of India / Government of Odisha") -> SourceCatalogEntry:
    return SourceCatalogEntry(id=id, family=family, title=title, uri=uri, origin=origin, publisher=publisher,
                              authority="official", granularity="district" if "facility" not in family else "facility", refresh_frequency="periodic",
                              currentness=currentness, notes=notes)


def sundargarh_profile() -> DistrictProfile:
    return DistrictProfile(
        id="sundargarh",
        display_name="Sundargarh",
        region="Odisha · India",
        state_or_region="Odisha",
        country="India",
        timezone="Asia/Kolkata",
        official_codes={"state": "OD", "district": "Sundargarh"},
        facility_source_family="official_facility_directory",
        stock_source_families=("amb_stock_dashboard",),
        programme_source_families=("amb_kpi_dashboard", "hmis_standard_reports"),
        policy_source_ref="https://www.nhm.gov.in/digigov-portal/index1.php?lang=1&level=3&lid=797&sublinkid=1448",
        supported_items=("ifa-red-60mg-500mcg",),
        commodity_profiles=("ifa-red-60mg-500mcg",),
        policy_profile="odisha-amb-ifa-2025",
        supported_languages=("en", "or"),
        data_freshness_rules={"district_stock_signal_days": 365, "facility_roster_days": 365},
        facility_source_config={"family": "official_facility_directory", "requires_official_id": False},
        programme_source_config={"families": ["amb_kpi_dashboard", "hmis_standard_reports"], "allocation_requires_uncertainty": True},
        source_catalog=(
            _source("amb-stock", "amb_stock_dashboard", "Anemia Mukt Bharat stock dashboard", "https://www.anemiamuktbharat.info/reports/stock", origin=Origin.OFFICIAL_PUBLIC_DATA),
            _source("amb-kpi", "amb_kpi_dashboard", "Anemia Mukt Bharat performance indicators", "https://www.anemiamuktbharat.info/reports/key-performance-indicators", origin=Origin.OFFICIAL_PUBLIC_DATA),
            _source("hmis", "hmis_standard_reports", "HMIS standard reports", "https://hmis.mohfw.gov.in/#!/standardReports", origin=Origin.OFFICIAL_SYSTEM_EXPORT),
            _source("facility-directory", "official_facility_directory", "Odisha official health facility directory", "https://health.odisha.gov.in/or/healthinstitutes/parathama-raepharaala-yaunaita", origin=Origin.OFFICIAL_PUBLIC_DATA),
            _source("google-routes", "route_provider", "Google Routes Compute Routes", "https://developers.google.com/maps/documentation/routes/compute_route_directions", origin=Origin.LIVE_EXTERNAL_API, publisher="Google Maps Platform", notes="Provider-backed route observations are persisted with request hashes; unavailable responses remain ROUTE_UNAVAILABLE."),
            _source("dvdms", "dvdms_inventory", "e-Niramaya / DVDMS", "https://niramaya-dvdms.odisha.gov.in/IMCS/init", origin=Origin.OFFICIAL_SYSTEM_EXPORT, notes="Login-gated; no public operational export captured."),
        ),
    )


def portability_profiles() -> tuple[DistrictProfile, ...]:
    """The same source families can be configured for other Odisha districts."""
    return (
        sundargarh_profile(),
        sundargarh_profile().model_copy(update={"id": "sambalpur", "display_name": "Sambalpur", "official_codes": {"state": "OD", "district": "Sambalpur"}}),
        sundargarh_profile().model_copy(update={"id": "kalahandi", "display_name": "Kalahandi", "official_codes": {"state": "OD", "district": "Kalahandi"}}),
    )
