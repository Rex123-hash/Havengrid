"""The Sundargarh fixture exposed through the DataSource contract.

This exists so the assembler, the environment guard and the API can treat the
synthetic scenario exactly like a real source — and refuse it where a real
source is required.
"""

from __future__ import annotations

from typing import Iterable

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
    SupplyLink,
)
from ..store import ScenarioState
from ..synthetic.sundargarh import build_sundargarh
from .contracts import SourceDescriptor


class SyntheticSundargarhSource:
    def __init__(self) -> None:
        self._st: ScenarioState = build_sundargarh()

    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            id="synthetic/sundargarh",
            origin=Origin.SYNTHETIC_TEST,
            description="Deterministic synthetic regression scenario. Not an observation of any real district.",
        )

    def district(self) -> District:
        return self._st.district

    def items(self) -> Iterable[Item]:
        return list(self._st.items.values())

    def facilities(self) -> Iterable[Facility]:
        return list(self._st.facilities.values())

    def links(self) -> Iterable[SupplyLink]:
        return list(self._st.links)

    def routes(self) -> Iterable[Route]:
        return list(self._st.routes.values())

    def inventory(self) -> Iterable[InventoryRecord]:
        return list(self._st.inventory.values())

    def batches(self) -> Iterable[Batch]:
        return list(self._st.batches.values())

    def demand_profiles(self) -> Iterable[DemandProfile]:
        return list(self._st.demand.values())

    def supplies(self) -> Iterable[IncomingSupply]:
        return list(self._st.supplies.values())

    def care_events(self) -> Iterable[CareEvent]:
        return list(self._st.care_events.values())

    def care_obligations(self) -> Iterable[CareObligation]:
        return list(self._st.care_obligations.values())
