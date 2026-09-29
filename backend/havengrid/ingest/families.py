"""Composable source-family contracts for district onboarding.

Each family can be backed by a different public, authenticated, or human
evidence source. The assembler is deliberately structural; it does not fetch,
merge, or promote facts by itself.
"""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from ..domain.models import CareObligation, DistrictCommodityStockSignal, Facility, ProgrammeActivity, Route, SupplyLink


@runtime_checkable
class AMBProgrammeSource(Protocol):
    def stock_signals(self) -> Iterable[DistrictCommodityStockSignal]: ...
    def programme_activity(self) -> Iterable[ProgrammeActivity]: ...


@runtime_checkable
class HMISActivitySource(Protocol):
    def programme_activity(self) -> Iterable[ProgrammeActivity]: ...


@runtime_checkable
class FacilityRegistrySource(Protocol):
    def facilities(self) -> Iterable[Facility]: ...
    def links(self) -> Iterable[SupplyLink]: ...


@runtime_checkable
class FieldEvidenceSource(Protocol):
    """Human-confirmed inventory and care evidence; never an auto-promoter."""
    def inventory_records(self): ...
    def care_obligations(self) -> Iterable[CareObligation]: ...


@runtime_checkable
class RouteSource(Protocol):
    def routes(self) -> Iterable[Route]: ...


class DistrictDataAssembler:
    """Selects source families for a profile without changing the kernel."""

    def __init__(self, profile, *, facility_sources=(), programme_sources=(), inventory_sources=(), route_sources=()):
        self.profile = profile
        self.facility_sources = tuple(facility_sources)
        self.programme_sources = tuple(programme_sources)
        self.inventory_sources = tuple(inventory_sources)
        self.route_sources = tuple(route_sources)

    def source_families(self) -> dict[str, int]:
        return {
            "facility": len(self.facility_sources),
            "programme": len(self.programme_sources),
            "inventory": len(self.inventory_sources),
            "route": len(self.route_sources),
        }
