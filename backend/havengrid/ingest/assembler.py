"""Builds a `ScenarioState` from any `DataSource`.

The kernel never sees the source. It sees canonical records with provenance.
Assembling from the synthetic source must round-trip exactly to
`build_sundargarh()`; a test proves it.
"""

from __future__ import annotations

from ..domain.enums import CaseState
from ..domain.models import RecoveryCase
from ..store import ScenarioState
from .contracts import DataSource, DataSourceUnavailable


def assemble(source: DataSource, *, open_case: tuple[str, str, str] | None = None) -> ScenarioState:
    """`open_case = (case_id, recipient_facility_id, item_id)` opens one recovery case.
    Case ids are workflow identity, not source data, so the caller names them."""
    district = source.district()
    st = ScenarioState(district=district)
    for item in source.items():
        st.items[item.id] = item
    for f in source.facilities():
        st.facilities[f.id] = f
    st.links.extend(source.links())
    for r in source.routes():
        st.routes[(r.from_id, r.to_id)] = r
    for rec in source.inventory():
        st.inventory[rec.id] = rec
    for p in source.demand_profiles():
        st.demand[(p.facility_id, p.item_id)] = p
    for s in source.supplies():
        st.supplies[s.id] = s
    for b in source.batches():
        st.batches[b.id] = b
    for e in source.care_events():
        st.care_events[e.id] = e
    for o in source.care_obligations():
        st.care_obligations[o.id] = o

    canonical = [(r.facility_id, r.item_id) for r in st.inventory.values() if r.canonical]
    if len(canonical) != len(set(canonical)):
        raise DataSourceUnavailable("inventory", "more than one canonical record for a facility+item")

    if open_case:
        cid, facility_id, item_id = open_case
        st.cases[cid] = RecoveryCase(id=cid, district_id=district.id, recipient_id=facility_id, item_id=item_id,
                                     state=CaseState.FORECASTED, opened_at=district.forecast_at)
    return st
