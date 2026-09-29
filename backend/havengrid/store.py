"""In-memory repository. The only persistence in Phase 0.

`Repository` is the seam a database implementation would fill later. Nothing
outside this module touches the dicts. Reset rebuilds the whole state from a
pure fixture function, so replay is exact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from .domain.errors import NotFound
from .domain.models import (
    AuditEvent,
    Batch,
    CareEvent,
    CareObligation,
    CareDeliveryRecord,
    DemandProfile,
    District,
    EvidenceRecord,
    Facility,
    IncomingSupply,
    InterventionPlan,
    InventoryRecord,
    Item,
    ReconciliationRecord,
    RecoveryCase,
    Route,
    SupplyLink,
    VerificationRecord,
    DistrictCommodityStockSignal,
    DistrictProfile,
    DistrictReadiness,
    ProgrammeActivity,
    RouteObservation,
)


@dataclass
class ScenarioState:
    """Everything the kernel and service need. Plain containers, all keyed by id."""

    district: District
    items: dict[str, Item] = field(default_factory=dict)
    facilities: dict[str, Facility] = field(default_factory=dict)
    links: list[SupplyLink] = field(default_factory=list)
    routes: dict[tuple[str, str], Route] = field(default_factory=dict)
    route_observations: dict[str, RouteObservation] = field(default_factory=dict)
    inventory: dict[str, InventoryRecord] = field(default_factory=dict)
    demand: dict[tuple[str, str], DemandProfile] = field(default_factory=dict)
    supplies: dict[str, IncomingSupply] = field(default_factory=dict)
    batches: dict[str, Batch] = field(default_factory=dict)
    care_events: dict[str, CareEvent] = field(default_factory=dict)
    care_obligations: dict[str, CareObligation] = field(default_factory=dict)
    care_delivery: dict[str, CareDeliveryRecord] = field(default_factory=dict)
    district_stock_signals: dict[str, DistrictCommodityStockSignal] = field(default_factory=dict)
    programme_activity: dict[str, ProgrammeActivity] = field(default_factory=dict)
    district_profile: DistrictProfile | None = None
    readiness: DistrictReadiness | None = None
    cases: dict[str, RecoveryCase] = field(default_factory=dict)
    plans: dict[str, InterventionPlan] = field(default_factory=dict)
    evidence: dict[str, EvidenceRecord] = field(default_factory=dict)
    verifications: dict[str, VerificationRecord] = field(default_factory=dict)
    reconciliations: dict[str, ReconciliationRecord] = field(default_factory=dict)
    audit: list[AuditEvent] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)


class Repository(Protocol):
    def state(self) -> ScenarioState: ...
    def reset(self) -> None: ...


class InMemoryRepository:
    def __init__(self, build: Callable[[], ScenarioState]) -> None:
        self._build = build
        self._state = build()

    def state(self) -> ScenarioState:
        return self._state

    def reset(self) -> None:
        self._state = self._build()

    # ── typed accessors (raise NotFound with a useful message) ────────────

    def facility(self, facility_id: str) -> Facility:
        try:
            return self._state.facilities[facility_id]
        except KeyError as e:
            raise NotFound(f"facility '{facility_id}' not found") from e

    def item(self, item_id: str) -> Item:
        try:
            return self._state.items[item_id]
        except KeyError as e:
            raise NotFound(f"item '{item_id}' not found") from e

    def case(self, case_id: str) -> RecoveryCase:
        try:
            return self._state.cases[case_id]
        except KeyError as e:
            raise NotFound(f"case '{case_id}' not found") from e

    def plan(self, plan_id: str) -> InterventionPlan:
        try:
            return self._state.plans[plan_id]
        except KeyError as e:
            raise NotFound(f"plan '{plan_id}' not found") from e

    def evidence(self, evidence_id: str) -> EvidenceRecord:
        try:
            return self._state.evidence[evidence_id]
        except KeyError as e:
            raise NotFound(f"evidence '{evidence_id}' not found") from e

    def canonical_inventory(self, facility_id: str, item_id: str) -> InventoryRecord | None:
        for rec in self._state.inventory.values():
            if rec.facility_id == facility_id and rec.item_id == item_id and rec.canonical:
                return rec
        return None

    def inventory_lineage(self, facility_id: str, item_id: str) -> list[InventoryRecord]:
        recs = [r for r in self._state.inventory.values() if r.facility_id == facility_id and r.item_id == item_id]
        return sorted(recs, key=lambda r: r.provenance.observed_at)

    def demand_profile(self, facility_id: str, item_id: str) -> DemandProfile | None:
        return self._state.demand.get((facility_id, item_id))

    def care_events_for(self, facility_id: str, item_id: str | None = None) -> list[CareEvent]:
        return [
            e for e in self._state.care_events.values()
            if e.facility_id == facility_id and (item_id is None or e.item_id == item_id)
        ]

    def care_obligations_for(self, facility_id: str, item_id: str | None = None) -> list[CareObligation]:
        return [
            o for o in self._state.care_obligations.values()
            if o.facility_id == facility_id and (item_id is None or o.item_id == item_id)
        ]

    def supplies_for(self, facility_id: str, item_id: str) -> list[IncomingSupply]:
        return [s for s in self._state.supplies.values() if s.destination_id == facility_id and s.item_id == item_id]

    def batches_for(self, facility_id: str, item_id: str) -> list[Batch]:
        return [b for b in self._state.batches.values() if b.facility_id == facility_id and b.item_id == item_id]

    def route(self, from_id: str, to_id: str) -> Route | None:
        return self._state.routes.get((from_id, to_id))

    def routes_into(self, to_id: str) -> list[Route]:
        return [r for r in self._state.routes.values() if r.to_id == to_id]

    def next_id(self, prefix: str) -> str:
        n = self._state.counters.get(prefix, 0) + 1
        self._state.counters[prefix] = n
        return f"{prefix}-{n:03d}"

    # ── writes ────────────────────────────────────────────────────────────

    def put_inventory(self, rec: InventoryRecord) -> None:
        self._state.inventory[rec.id] = rec

    def put_supply(self, s: IncomingSupply) -> None:
        self._state.supplies[s.id] = s

    def put_case(self, c: RecoveryCase) -> None:
        self._state.cases[c.id] = c

    def put_plan(self, p: InterventionPlan) -> None:
        self._state.plans[p.id] = p

    def put_evidence(self, e: EvidenceRecord) -> None:
        self._state.evidence[e.id] = e

    def put_verification(self, v: VerificationRecord) -> None:
        self._state.verifications[v.id] = v

    def put_reconciliation(self, r: ReconciliationRecord) -> None:
        self._state.reconciliations[r.id] = r

    def put_care_delivery(self, r: CareDeliveryRecord) -> None:
        self._state.care_delivery[r.id] = r

    def put_route_observation(self, r: RouteObservation) -> None:
        self._state.route_observations[r.id] = r

    def append_audit(self, ev: AuditEvent) -> None:
        self._state.audit.append(ev)

    def audit_for(self, case_id: str | None = None) -> list[AuditEvent]:
        return [a for a in self._state.audit if case_id is None or a.case_id == case_id]

    def all_facilities(self) -> Iterable[Facility]:
        return self._state.facilities.values()
