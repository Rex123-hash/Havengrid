"""Response/request DTOs. Persistence models never leak through the API.

Every response carries `synthetic: true`. The frontend adapter relies on
`ScenarioBundle` and fails loudly if a backend-authoritative field is missing.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.enums import (
    CandidateVerdict,
    CareCategory,
    CaseAction,
    CaseState,
    EvidenceState,
    FacilityTier,
    ForecastStatus,
    RejectionReason,
    VerificationKind,
    VerificationOutcome,
    ReconciliationOutcome,
    CoverageRecoveryStatus,
    EvidenceGrade,
    CurrentnessStatus,
    ReadinessStatus,
    ExposureKind,
    CareDeliveryOutcome,
    FacilityInventoryStatus,
)


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProvenanceOut(DTO):
    source_type: str
    status: str
    observed_at: datetime
    source_ref: str
    origin: str
    confidence: Decimal
    note: str
    publisher: str | None = None
    source_period: str | None = None
    retrieved_at: datetime | None = None
    geographic_granularity: str | None = None
    source_hash: str | None = None
    quality_flags: list[str] = []


class FacilityOut(DTO):
    id: str
    name: str
    short_name: str
    tier: FacilityTier
    x: int
    y: int
    block: str | None = None
    official_identifier: str | None = None
    source_ref: str | None = None
    source_date: datetime | None = None
    currentness: str = "unknown"
    coordinate_source: str = "schematic"
    facility_type: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    coordinate_provenance: ProvenanceOut | None = None


class LinkOut(DTO):
    from_id: str
    to_id: str


class ProjectionRowOut(DTO):
    day: int
    opening: int
    credit: int
    demand: int
    closing: int
    cover_required: int
    covered: bool


class ForecastOut(DTO):
    facility_id: str
    item_id: str
    status: ForecastStatus
    as_of: datetime
    inventory_record_id: str | None
    starting_inventory: int | None
    coverage_breach_day: int | None
    coverage_breach_at: datetime | None
    stockout_day: int | None
    stockout_at: datetime | None
    recovery_day: int | None
    recovery_at: datetime | None
    projected_demand_window: int | None = Field(description="Σ demand over the planning window")
    gap_window: int | None = Field(description="projected_demand_window − starting_inventory")
    projection: list[ProjectionRowOut]
    drivers: list[str]
    derived_from: DerivedFromOut | None = None


class CareImpactOut(DTO):
    facility_id: str
    status: ForecastStatus
    coverage_breach_day: int | None
    recovery_day: int | None
    scheduled_in_window: int
    exposed_total: int | None
    exposed_by_category: dict[CareCategory, int] | None
    exposed_event_ids: list[str]
    exposed_obligation_ids: list[str] = []
    exposed_units: int | None
    unserved_total: int | None
    unserved_event_ids: list[str]
    unserved_obligation_ids: list[str] = []
    derived_from: DerivedFromOut | None = None


class CareEventOut(DTO):
    id: str
    facility_id: str
    category: CareCategory
    scheduled_at: datetime
    day: int
    units_required: int
    description: str
    exposed: bool | None
    unserved: bool | None


class AllocationOut(DTO):
    batch_id: str
    quantity: int
    expires_at: datetime | None


class CandidateOut(DTO):
    donor_id: str
    donor_name: str
    quantity: int
    donor_inventory: int | None
    transferable: int
    donor_protection_window_days: int
    donor_coverage_breach_day: int | None
    donor_post_transfer_breach_day: int | None
    donor_post_transfer_margin: int
    distance_km: Decimal
    transit_hours: Decimal
    dispatch_ready_at: datetime
    expected_arrival_at: datetime
    arrival_day: int
    recipient_post_transfer_breach_day: int | None
    allocations: list[AllocationOut]
    expiry_relief: bool
    feasible: bool
    checks: dict[str, bool]
    rejection_reasons: list[RejectionReason]
    explanations: list[str] = Field(description="Generated from reason codes; never stored prose")
    rank: int | None
    rank_components: dict[str, object]
    verdict: CandidateVerdict
    derived_from: DerivedFromOut | None = None


class PlanOut(DTO):
    id: str
    case_id: str
    recipient_id: str
    required_quantity: int
    hold_through_day: int
    chosen_donor_id: str | None
    candidates: list[CandidateOut]
    evaluated_at: datetime
    invalidated: bool
    invalidation_reason: RejectionReason | None
    superseded_by_id: str | None
    derived_from: DerivedFromOut | None = None


class InventoryRecordOut(DTO):
    id: str
    facility_id: str
    quantity: int
    canonical: bool
    supersedes_id: str | None
    superseded_by_id: str | None
    evidence_id: str | None
    provenance: ProvenanceOut


class EvidenceOut(DTO):
    id: str
    case_id: str
    facility_id: str
    observed_quantity: int
    confidence: Decimal
    source_type: str
    captured_via: str
    observed_at: datetime
    state: EvidenceState
    canonical_quantity_at_submission: int | None
    canonical_record_id_at_submission: str | None
    evidence_class: str = "USER_SUPPLIED_EVIDENCE"
    committed_record_id: str | None
    decided_at: datetime | None
    decided_by: str | None


class VerificationOut(DTO):
    id: str
    kind: VerificationKind
    expected: str
    observed: str | None
    outcome: VerificationOutcome
    verified_at: datetime
    verified_by: str
    note: str


class ReconciliationOut(DTO):
    id: str
    at: datetime
    outcome: ReconciliationOutcome
    originally_exposed_ids: list[str]
    still_exposed_ids: list[str]
    protected_count: int
    note: str
    coverage_status: CoverageRecoveryStatus = CoverageRecoveryStatus.COVERAGE_NOT_RESTORED
    coverage_restored_count: int = 0
    originally_exposed_refs: list[dict[str, str]] = []
    still_exposed_refs: list[dict[str, str]] = []


class DerivedFromOut(DTO):
    record_type: str
    record_ids: list[str]
    source_refs: list[str]
    note: str


class CareDeliveryOut(DTO):
    id: str
    case_id: str
    exposure: dict[str, str]
    outcome: CareDeliveryOutcome
    verified_at: datetime
    verified_by: str
    source_ref: str
    note: str


class AuditOut(DTO):
    seq: int
    at: datetime
    action: str
    from_state: CaseState | None
    to_state: CaseState | None
    detail: dict[str, object]


class CaseOut(DTO):
    id: str
    district_id: str
    recipient_id: str
    item_id: str
    state: CaseState
    legal_actions: list[CaseAction]
    plan_id: str | None
    previous_plan_ids: list[str]
    evidence_ids: list[str]
    verification_ids: list[str]
    reconciliation_ids: list[str]
    originally_exposed_ids: list[str]
    originally_exposed_refs: list[dict[str, str]] = []
    care_delivery_ids: list[str] = []
    transfer_supply_id: str | None
    care_protected_count: int | None
    closed_at: datetime | None


class FacilityDetailOut(DTO):
    facility: FacilityOut
    canonical_inventory: InventoryRecordOut | None
    inventory_lineage: list[InventoryRecordOut]
    forecast: ForecastOut
    care_impact: CareImpactOut
    care_events: list[CareEventOut]
    days_since_physical_count: int | None
    inventory_status: FacilityInventoryStatus = FacilityInventoryStatus.INVENTORY_REQUIRED


class ItemOut(DTO):
    id: str
    name: str
    form: str
    unit: str
    pack_size: int
    physical_dispatch_unit: str = "UNKNOWN"
    dose_rules: list[dict[str, object]] = []


class PolicyOut(DTO):
    min_cover_days: int
    planning_window_days: int
    horizon_days: int
    dispatch_lead_hours: dict[str, Decimal]
    policy_minimum_cover_days: int | None = None
    havengrid_continuity_threshold_days: int | None = None


class DistrictOut(DTO):
    id: str
    name: str
    region: str
    timezone: str
    forecast_at: datetime
    policy: PolicyOut


class DataOriginOut(DTO):
    """WHERE DID THESE NUMBERS COME FROM? Distinct fact origins in the current state."""

    source_id: str
    origins: list[str]
    synthetic: bool = Field(description="true iff every fact record is synthetic_test")
    environment: str


class SourceCatalogEntryOut(DTO):
    id: str
    family: str
    title: str
    uri: str
    origin: str
    access: str
    publisher: str
    authority: str
    granularity: str
    refresh_frequency: str
    license: str
    supported_fields: list[str]
    unsupported_fields: list[str]
    currentness: CurrentnessStatus
    current_status: CurrentnessStatus | None
    last_checked_at: datetime | None
    notes: str


class DistrictProfileOut(DTO):
    id: str
    display_name: str
    region: str
    state_or_region: str | None
    country: str
    timezone: str
    official_codes: dict[str, str]
    source_catalog: list[SourceCatalogEntryOut]
    facility_source_family: str
    stock_source_families: list[str]
    programme_source_families: list[str]
    policy_source_ref: str
    coordinate_policy: str
    supported_items: list[str]
    facility_source_config: dict[str, object]
    programme_source_config: dict[str, object]
    commodity_profiles: list[str]
    policy_profile: str
    supported_languages: list[str]
    data_freshness_rules: dict[str, int]


class DistrictCommodityStockSignalOut(DTO):
    id: str
    district_id: str
    item_id: str
    period: str
    opening_balance: Decimal | None
    received: Decimal | None
    distributed: Decimal | None
    unusable: Decimal | None
    available: Decimal | None
    unit: str
    geographic_granularity: str
    source_ref: str
    source_hash: str
    retrieved_at: datetime | None
    quality_flags: list[str] = []
    provenance: ProvenanceOut


class RouteObservationOut(DTO):
    id: str
    from_id: str
    to_id: str
    distance_km: Decimal | None
    duration_hours: Decimal | None
    static_duration_hours: Decimal | None
    retrieved_at: datetime
    provider: str
    request_hash: str
    status: str
    provenance: ProvenanceOut
    error: str | None = None


class DistrictReadinessOut(DTO):
    district_id: str
    facility_roster: ReadinessStatus
    programme_activity: ReadinessStatus
    district_stock_context: ReadinessStatus
    facility_inventory: ReadinessStatus
    routes: ReadinessStatus
    care_obligations: ReadinessStatus
    policy: ReadinessStatus
    reasons: list[str]


class ProgrammeActivityOut(DTO):
    id: str
    district_id: str
    period: str
    indicator: str
    value: Decimal | None
    unit: str
    evidence_grade: EvidenceGrade
    basis: str
    allocation_method: str | None
    uncertainty: Decimal | None
    derived_from: list[str]
    provenance: ProvenanceOut


class NetworkOut(DTO):
    district: DistrictOut
    item: ItemOut
    facilities: list[FacilityOut]
    links: list[LinkOut]
    forecasts: dict[str, ForecastOut]
    care_impacts: dict[str, CareImpactOut]
    data_origin: DataOriginOut
    synthetic: bool


class ScenarioBundle(DTO):
    """Everything the landing-page adapter needs, in one call."""

    synthetic: bool
    data_origin: DataOriginOut
    district: DistrictOut
    item: ItemOut
    facilities: list[FacilityOut]
    links: list[LinkOut]
    forecasts: dict[str, ForecastOut]
    care_impacts: dict[str, CareImpactOut]
    focus_facility_id: str
    focus_care_events: list[CareEventOut]
    case: CaseOut
    plan: PlanOut | None
    previous_plans: list[PlanOut]
    evidence: list[EvidenceOut]
    inventory_lineage: dict[str, list[InventoryRecordOut]]
    verifications: list[VerificationOut]
    reconciliations: list[ReconciliationOut]
    inventory_freshness: dict[str, int | None] = Field(description="days since last physical count per facility; null = no canonical record")
    clock_now: datetime
    route_observations: list[RouteObservationOut] = []


class WorkspaceMetadataOut(DTO):
    district: DistrictOut
    mode: str
    designation: str
    commodity: ItemOut
    clock_now: datetime
    data_origin: DataOriginOut


class WorkspaceFacilityOut(DTO):
    facility: FacilityOut
    inventory_status: FacilityInventoryStatus
    canonical_inventory: InventoryRecordOut | None
    forecast: ForecastOut
    care_impact: CareImpactOut
    days_since_physical_count: int | None


class WorkspaceNetworkOut(DTO):
    facilities: list[WorkspaceFacilityOut]
    links: list[LinkOut]
    route_observations: list[RouteObservationOut]


class WorkspaceEvidenceOut(DTO):
    evidence: EvidenceOut
    current_canonical_quantity: int | None
    current_inventory_status: FacilityInventoryStatus


class CareObligationBasisOut(DTO):
    id: str
    facility_id: str
    expected_attendance: int
    estimated_population_min: int | None
    estimated_population_max: int | None
    evidence_grade: EvidenceGrade
    numeric_basis_origin: str
    public_programme_basis: str | None
    facility_denominator_status: str
    basis: str
    uncertainty_note: str
    provenance: ProvenanceOut


class WorkspaceIntelligenceOut(DTO):
    profile: DistrictProfileOut | None
    readiness: DistrictReadinessOut
    stock_signals: list[DistrictCommodityStockSignalOut]
    programme_activity: list[ProgrammeActivityOut]
    care_obligations: list[CareObligationBasisOut]


class WorkspaceRecoveryOut(DTO):
    state: CaseState
    completed_audit_actions: list[str]
    domain_legal_actions: list[CaseAction]
    authorization_status: Literal["not_evaluated"] = "not_evaluated"
    coverage_status: CoverageRecoveryStatus | Literal["not_verified"]
    care_protected: bool
    care_delivery: list[CareDeliveryOut]


class WorkspaceSnapshotOut(DTO):
    metadata: WorkspaceMetadataOut
    network: WorkspaceNetworkOut
    active_case: CaseOut
    recipient_forecast: ForecastOut
    recipient_care_impact: CareImpactOut
    current_plan: PlanOut | None
    previous_plans: list[PlanOut]
    evidence: list[WorkspaceEvidenceOut]
    recovery: WorkspaceRecoveryOut
    intelligence: WorkspaceIntelligenceOut
    limitations: list[str]


# ── requests ────────────────────────────────────────────────────────────────


class EvidenceIn(DTO):
    facility_id: str
    observed_quantity: int = Field(ge=0)
    confidence: Decimal = Field(ge=0, le=1)
    captured_via: str = "field photograph · ward stock register"
    evidence_class: str = "USER_SUPPLIED_EVIDENCE"
    command_id: str | None = None


class DecisionIn(DTO):
    actor: str = "district-pharmacist"
    note: str = ""
    command_id: str | None = None


class AdvanceIn(DTO):
    action: CaseAction
    actor: str = "demo-operator"
    observed_quantity: int | None = None
    observed_batch_ids: list[str] | None = None
    command_id: str | None = None


class CareDeliveryIn(DTO):
    exposure_kind: ExposureKind
    exposure_id: str
    outcome: CareDeliveryOutcome
    verified_by: str = "district-operator"
    source_ref: str
    note: str = ""
    command_id: str | None = None


class ErrorOut(DTO):
    code: str
    message: str
    detail: dict[str, object] = Field(default_factory=dict)
