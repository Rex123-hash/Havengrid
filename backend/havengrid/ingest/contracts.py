"""Real-data adapter boundary.

The deterministic kernel consumes canonical domain records (`havengrid.domain.models`)
and does not care where they came from. A `DataSource` is anything that can
produce those records with honest provenance. This module defines the contract;
it deliberately contains NO fetching, scraping or parsing.

Implementations:
    havengrid.ingest.synthetic_source.SyntheticSundargarhSource   (tests / dev)
    havengrid.ingest.unavailable_source.UnavailableSource         (degraded mode)
    … official sources arrive in a later phase behind the same Protocols.

Every method returns records whose `provenance.origin` truthfully states the
source class (OFFICIAL_PUBLIC_DATA, OFFICIAL_SYSTEM_EXPORT, USER_SUPPLIED_EVIDENCE,
LIVE_EXTERNAL_API, or SYNTHETIC_TEST). An implementation that cannot supply a
family raises `DataSourceUnavailable` rather than returning an empty list, so
"nothing scheduled" is never confused with "we could not find out".

Required fields per family (what an official source must be able to provide):

FACILITY METADATA (`facilities`, `links`)
    id · name · tier (warehouse/CHC/PHC) · district · parent for routine resupply
    schematic position may be synthesised for display; geography is optional.

INVENTORY OBSERVATIONS (`inventory`)
    facility · item · quantity · observed_at · source_type (ledger / physical count)
    · confidence · last physical count date. One canonical record per facility+item.

HISTORICAL CONSUMPTION (`demand_profiles`)
    facility · item · daily dispensing series (or a rate with the period it was
    measured over) · the period/method used. This is the baseline; scheduled
    care is NOT included in it.

INCOMING SUPPLY (`supplies`)
    destination · source · item · quantity · expected_arrival_at (timestamp, not
    "in 13 days") · state.

CARE / SERVICE ACTIVITY (`care_events`, `care_obligations`)
    Per-encounter rows are OPTIONAL and must be PHI-free (opaque id only).
    Aggregated obligations are the expected shape: facility · category ·
    session_at · expected_attendance · item · units_per_attendance (+ cited basis).

BATCH / EXPIRY (`batches`)
    facility · item · batch id · quantity · expiry timestamp.

ROUTE / TRAVEL TIME (`routes`)
    from · to · distance · transit hours · (dispatch lead by tier lives in policy).

POLICY (`district`)
    min_cover_days · planning_window_days · horizon_days · dispatch lead hours,
    each with a policy reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, runtime_checkable

from ..domain.enums import Origin
from ..domain.models import (
    Batch,
    CareEvent,
    CareObligation,
    DemandProfile,
    District,
    Facility,
    IncomingSupply,
    InventoryRecord,
    Item,
    Route,
    RouteObservation,
    SupplyLink,
)


class DataSourceUnavailable(RuntimeError):
    """The source exists but cannot currently supply this family of records."""

    def __init__(self, family: str, reason: str) -> None:
        super().__init__(f"{family}: {reason}")
        self.family = family
        self.reason = reason


@dataclass(frozen=True)
class SourceDescriptor:
    """Who this source is, for /health and for stamping provenance."""

    id: str
    origin: Origin
    description: str


@runtime_checkable
class FacilitySource(Protocol):
    def district(self) -> District: ...
    def items(self) -> Iterable[Item]: ...
    def facilities(self) -> Iterable[Facility]: ...
    def links(self) -> Iterable[SupplyLink]: ...
    def routes(self) -> Iterable[Route]: ...


@runtime_checkable
class InventorySource(Protocol):
    def inventory(self) -> Iterable[InventoryRecord]: ...
    def batches(self) -> Iterable[Batch]: ...


@runtime_checkable
class ConsumptionSource(Protocol):
    def demand_profiles(self) -> Iterable[DemandProfile]: ...


@runtime_checkable
class SupplySource(Protocol):
    def supplies(self) -> Iterable[IncomingSupply]: ...


@runtime_checkable
class CareActivitySource(Protocol):
    def care_events(self) -> Iterable[CareEvent]: ...
    def care_obligations(self) -> Iterable[CareObligation]: ...


@runtime_checkable
class RouteObservationSource(Protocol):
    """Provider-backed route observations, including explicit unavailable results."""

    def route_observations(self) -> Iterable[RouteObservation]: ...


@runtime_checkable
class DataSource(FacilitySource, InventorySource, ConsumptionSource, SupplySource, CareActivitySource, Protocol):
    def descriptor(self) -> SourceDescriptor: ...
