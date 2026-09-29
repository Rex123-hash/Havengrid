"""Canonical domain models (revised at the Phase 0A gate).

Four kinds of thing, kept apart:

  FACTS        Facility, Item, Batch, InventoryRecord, IncomingSupply,
               DemandProfile, CareEvent, Route, CoverPolicy — each with Provenance.
  PREDICTIONS  CoverageAssessment, CareImpact — kernel output, never authored.
  PROPOSALS    InterventionCandidate, InterventionPlan — kernel output with
               structured checks and reason codes.
  WORKFLOW     EvidenceRecord, RecoveryCase, VerificationRecord,
               ReconciliationRecord, AuditEvent.

Units are discrete calculation units. Physical dispatch packaging is carried
separately on `Item.physical_dispatch_unit`; it remains UNKNOWN when a source
does not publish pack data. Decimal is used only where fractional precision is
genuinely meaningful (confidence, distance, hours).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    CandidateVerdict,
    CareCategory,
    CaseState,
    EvidenceState,
    FacilityTier,
    ForecastStatus,
    IncomingSupplyState,
    Origin,
    ProvenanceStatus,
    ReconciliationOutcome,
    RejectionReason,
    SourceType,
    VerificationKind,
    VerificationOutcome,
    CareDeliveryOutcome,
    CurrentnessStatus,
    EvidenceGrade,
    ExposureKind,
    ReadinessStatus,
    CoverageRecoveryStatus,
    SourceQualityFlag,
    RouteObservationStatus,
)

FacilityId = Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9\-]+$")]
ItemId = Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9\-]+$")]
Units = Annotated[int, Field(ge=0)]
Day = Annotated[int, Field(ge=0)]

DAY = timedelta(hours=24)
RETRIEVAL_CLOCK_SKEW = timedelta(minutes=5)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_retrieved_at(value: datetime, *, now: datetime | None = None,
                          tolerance: timedelta = RETRIEVAL_CLOCK_SKEW) -> datetime:
    """Reject source retrieval times materially ahead of the trusted UTC clock.

    The source timestamp is never rewritten. A caller may inject ``now`` for
    deterministic tests and a small clock-skew tolerance is permitted.
    """
    if value.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware (UTC)")
    trusted = now or utcnow()
    if value > trusted + tolerance:
        raise ValueError(f"retrieved_at {value.isoformat()} is ahead of trusted clock {trusted.isoformat()}")
    return value


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Mutable(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ── provenance ──────────────────────────────────────────────────────────────


class Provenance(Frozen):
    source_type: SourceType
    status: ProvenanceStatus
    observed_at: datetime
    source_ref: str
    origin: Origin
    confidence: Decimal = Field(ge=0, le=1, default=Decimal("1"))
    note: str = ""
    publisher: str | None = None
    source_period: str | None = None
    retrieved_at: datetime | None = None
    geographic_granularity: str | None = None
    source_hash: str | None = None
    quality_flags: tuple[SourceQualityFlag, ...] = ()

    @property
    def is_synthetic(self) -> bool:
        return self.origin is Origin.SYNTHETIC_TEST

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware (UTC)")
        return v

    @field_validator("retrieved_at")
    @classmethod
    def _provenance_retrieved_not_in_future(cls, v: datetime | None) -> datetime | None:
        return None if v is None else validate_retrieved_at(v)


class SourceCatalogEntry(Frozen):
    """A citable source family with an explicit access and freshness contract."""

    id: str
    family: str
    title: str
    uri: str
    origin: Origin
    access: str = "public"
    publisher: str = ""
    authority: str = "official"
    granularity: str = "district"
    refresh_frequency: str = "unknown"
    license: str = "unknown"
    supported_fields: tuple[str, ...] = ()
    unsupported_fields: tuple[str, ...] = ()
    currentness: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    current_status: CurrentnessStatus | None = None
    last_checked_at: datetime | None = None
    notes: str = ""


class DistrictProfile(Frozen):
    """Configuration seam for district-specific source families and policy."""

    id: str
    display_name: str
    region: str
    state_or_region: str | None = None
    country: str = "India"
    timezone: str
    official_codes: dict[str, str] = Field(default_factory=dict)
    source_catalog: tuple[SourceCatalogEntry, ...] = ()
    facility_source_family: str = "official_facility_directory"
    stock_source_families: tuple[str, ...] = ()
    programme_source_families: tuple[str, ...] = ()
    policy_source_ref: str = ""
    coordinate_policy: str = "schematic_until_official_coordinates"
    supported_items: tuple[str, ...] = ()
    facility_source_config: dict[str, object] = Field(default_factory=dict)
    programme_source_config: dict[str, object] = Field(default_factory=dict)
    commodity_profiles: tuple[str, ...] = ()
    policy_profile: str = ""
    supported_languages: tuple[str, ...] = ("en",)
    data_freshness_rules: dict[str, int] = Field(default_factory=dict)


class UnitsRule(Frozen):
    """Explicit programme-to-dispensing-unit conversion rule."""

    id: str
    description: str
    numerator: str
    denominator: str
    units_per_person: Decimal = Field(gt=0)
    source_ref: str
    evidence_grade: EvidenceGrade = EvidenceGrade.DIRECTLY_LINKED


class IFADoseRule(Frozen):
    """One policy phase of the national red-IFA regime.

    Antenatal and postpartum continuation are deliberately separate rows; a
    single combined "180-day pregnancy/postpartum" rule would be ambiguous.
    """

    id: str
    quantity: Decimal = Field(gt=0)
    unit: str
    frequency: str
    population: str
    programme_phase: str
    duration_days: int = Field(gt=0)
    basis_ref: str
    evidence_grade: EvidenceGrade = EvidenceGrade.DIRECTLY_LINKED


# ── policies ────────────────────────────────────────────────────────────────


class CoverPolicy(Frozen):
    """District policy. Every number here has a stated rationale in the fixture."""

    min_cover_days: int = Field(gt=0)
    planning_window_days: int = Field(gt=0)
    horizon_days: int = Field(gt=0)
    dispatch_lead_hours: dict[FacilityTier, Decimal]
    provenance: Provenance
    policy_minimum_cover_days: int | None = None
    havengrid_continuity_threshold_days: int | None = None


# ── facts ───────────────────────────────────────────────────────────────────


class District(Frozen):
    id: str
    name: str
    region: str
    timezone: str
    forecast_at: datetime   # T0: start of day 1
    policy: CoverPolicy

    def day_start(self, day: int) -> datetime:
        return self.forecast_at + DAY * (day - 1)

    def day_end(self, day: int) -> datetime:
        return self.forecast_at + DAY * day

    def bucket_of(self, at: datetime) -> int:
        """1-based day bucket containing `at`; 0 for anything before T0."""
        if at < self.forecast_at:
            return 0
        return int((at - self.forecast_at) // DAY) + 1


class SchematicPosition(Frozen):
    x: int
    y: int


class Facility(Frozen):
    id: FacilityId
    name: str
    short_name: str
    tier: FacilityTier
    district_id: str
    position: SchematicPosition
    block: str | None = None
    official_identifier: str | None = None
    source_ref: str | None = None
    source_date: datetime | None = None
    currentness: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    coordinate_source: str = "schematic"
    facility_type: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    coordinate_provenance: Provenance | None = None


class SupplyLink(Frozen):
    """Structural network edge (parent → child routine resupply). Descriptive."""

    from_id: FacilityId
    to_id: FacilityId


class Route(Frozen):
    """A usable emergency-transfer route. Only pairs with a Route are candidates."""

    from_id: FacilityId
    to_id: FacilityId
    distance_km: Decimal = Field(ge=0)
    transit_hours: Decimal = Field(ge=0)
    provenance: Provenance
    static_transit_hours: Decimal | None = Field(default=None, ge=0)
    provider: str = "unknown"
    request_hash: str | None = None
    status: RouteObservationStatus = RouteObservationStatus.OK
    retrieved_at: datetime | None = None

    @field_validator("retrieved_at")
    @classmethod
    def _route_retrieved_not_in_future(cls, v: datetime | None) -> datetime | None:
        return None if v is None else validate_retrieved_at(v)


class Coordinate(Frozen):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    source_ref: str
    source: str
    retrieved_at: datetime | None = None

    @field_validator("retrieved_at")
    @classmethod
    def _coordinate_retrieved_not_in_future(cls, v: datetime | None) -> datetime | None:
        return None if v is None else validate_retrieved_at(v)


class Item(Frozen):
    id: ItemId
    name: str
    form: str
    unit: str
    pack_size: int = Field(gt=0)
    physical_dispatch_unit: str = "UNKNOWN"
    units_rule: UnitsRule | None = None
    dose_rules: tuple[IFADoseRule, ...] = ()


class Batch(Frozen):
    id: str
    facility_id: FacilityId
    item_id: ItemId
    quantity: Units
    expires_at: datetime | None
    provenance: Provenance


class InventoryRecord(Frozen):
    """One claim about how much a facility holds. Exactly one is canonical per
    (facility, item). Lineage is explicit: nothing is overwritten."""

    id: str
    facility_id: FacilityId
    item_id: ItemId
    quantity: Units
    provenance: Provenance
    canonical: bool
    supersedes_id: str | None = None
    superseded_by_id: str | None = None
    evidence_id: str | None = None


class DemandProfile(Frozen):
    """Baseline walk-in dispensing per day (excludes scheduled care events)."""

    facility_id: FacilityId
    item_id: ItemId
    daily: tuple[int, ...]
    shape_note: str
    provenance: Provenance

    @field_validator("daily")
    @classmethod
    def _valid(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if not v or any(x < 0 for x in v):
            raise ValueError("daily must be non-empty and non-negative")
        return v


class IncomingSupply(Frozen):
    id: str
    destination_id: FacilityId
    source_id: FacilityId | None
    item_id: ItemId
    quantity: Units
    expected_arrival_at: datetime
    state: IncomingSupplyState
    provenance: Provenance
    batch_id: str | None = None


class CareEvent(Frozen):
    """One scheduled care encounter. Carries NO personal information — only an
    opaque id, a category, a time and the stock it will consume. Real sources
    that cannot expose per-encounter rows should use `CareObligation` instead."""

    id: str
    facility_id: FacilityId
    category: CareCategory
    scheduled_at: datetime
    item_id: ItemId
    units_required: Units = Field(description="dispensing units this encounter is expected to consume")
    description: str
    provenance: Provenance


class CareObligation(Frozen):
    """An AGGREGATED care commitment — a clinic session, an immunisation day, a
    projected service load — with an expected attendance rather than named
    encounters. This is the privacy-preserving shape most official sources can
    supply. The kernel treats it as `expected_attendance` encounters on
    `session_at`, each consuming `units_per_attendance`."""

    id: str
    facility_id: FacilityId
    category: CareCategory
    session_at: datetime
    item_id: ItemId
    expected_attendance: int = Field(ge=0)
    units_per_attendance: Units
    description: str
    provenance: Provenance
    units_basis: str = Field(default="", description="Where units_per_attendance came from (EDL / STG / policy ref). Required outside synthetic origin.")
    estimated_population_min: int | None = Field(default=None, ge=0)
    estimated_population_max: int | None = Field(default=None, ge=0)
    tablets_required_min: int | None = Field(default=None, ge=0)
    tablets_required_max: int | None = Field(default=None, ge=0)
    uncertainty_note: str = ""
    evidence_grade: EvidenceGrade = EvidenceGrade.DIRECTLY_LINKED
    basis: str = ""
    allocation_method: str | None = None
    numeric_basis_origin: str = "UNKNOWN"
    public_programme_basis: str | None = None
    facility_denominator_status: str = "UNKNOWN"

    @model_validator(mode="after")
    def _range(self) -> "CareObligation":
        if self.estimated_population_min is not None and self.estimated_population_max is not None and self.estimated_population_min > self.estimated_population_max:
            raise ValueError("estimated population range is inverted")
        if self.tablets_required_min is not None and self.tablets_required_max is not None and self.tablets_required_min > self.tablets_required_max:
            raise ValueError("tablet requirement range is inverted")
        if self.evidence_grade is EvidenceGrade.PROGRAMME_ESTIMATED and (
            not self.basis or not self.allocation_method or not self.uncertainty_note
            or self.numeric_basis_origin == "UNKNOWN" or not self.public_programme_basis
            or self.facility_denominator_status == ""
        ):
            raise ValueError("PROGRAMME_ESTIMATED obligation requires explicit numeric/public/denominator provenance")
        return self


class DistrictCommodityStockSignal(Frozen):
    """District-level stock context. It must never be used as facility inventory."""

    id: str
    district_id: str
    item_id: ItemId
    period: str
    opening_balance: Decimal | None = None
    received: Decimal | None = None
    distributed: Decimal | None = None
    unusable: Decimal | None = None
    available: Decimal | None = None
    unit: str = "dispensing unit"
    geographic_granularity: str = "district"
    source_ref: str
    source_hash: str
    retrieved_at: datetime | None = None
    quality_flags: tuple[SourceQualityFlag, ...] = ()
    provenance: Provenance

    @field_validator("retrieved_at")
    @classmethod
    def _stock_retrieved_not_in_future(cls, v: datetime | None) -> datetime | None:
        return None if v is None else validate_retrieved_at(v)

class RouteObservation(Frozen):
    """Persisted route-provider response, including unavailable responses."""

    id: str
    from_id: FacilityId
    to_id: FacilityId
    distance_km: Decimal | None = Field(default=None, ge=0)
    duration_hours: Decimal | None = Field(default=None, ge=0)
    static_duration_hours: Decimal | None = Field(default=None, ge=0)
    retrieved_at: datetime
    provider: str
    request_hash: str
    status: RouteObservationStatus
    provenance: Provenance
    error: str | None = None

    @field_validator("retrieved_at")
    @classmethod
    def _route_observation_retrieved_not_in_future(cls, v: datetime) -> datetime:
        return validate_retrieved_at(v)


class ProgrammeActivity(Frozen):
    """Aggregated public programme activity with an honest evidence grade."""

    id: str
    district_id: str
    period: str
    indicator: str
    value: Decimal | None = None
    unit: str
    evidence_grade: EvidenceGrade
    basis: str
    allocation_method: str | None = None
    uncertainty: Decimal | None = Field(default=None, ge=0, le=1)
    derived_from: tuple[str, ...] = ()
    provenance: Provenance

    @model_validator(mode="after")
    def _evidence_contract(self) -> "ProgrammeActivity":
        if self.evidence_grade is EvidenceGrade.NOT_SUPPORTED and self.value is not None:
            raise ValueError("NOT_SUPPORTED programme activity must not emit a numeric value")
        if self.evidence_grade is EvidenceGrade.PROGRAMME_ESTIMATED:
            if not self.basis or not self.allocation_method or self.uncertainty is None or not self.derived_from:
                raise ValueError("PROGRAMME_ESTIMATED activity requires basis, allocation_method, uncertainty, and derived_from")
        return self


class DerivedFrom(Frozen):
    """Lineage for a derived value; source refs remain inspectable."""

    record_type: str
    record_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    note: str = ""


class DistrictReadiness(Frozen):
    district_id: str
    facility_roster: ReadinessStatus
    programme_activity: ReadinessStatus
    district_stock_context: ReadinessStatus
    facility_inventory: ReadinessStatus
    routes: ReadinessStatus
    care_obligations: ReadinessStatus
    policy: ReadinessStatus = ReadinessStatus.READY
    reasons: tuple[str, ...] = ()


# ── predictions ─────────────────────────────────────────────────────────────


class ProjectionRow(Frozen):
    day: Day
    opening: int
    credit: Units
    demand: Units
    closing: int
    cover_required: Units
    covered: bool


class CoverageAssessment(Frozen):
    """Forecast contract. Replaceable by any model that emits the same shape."""

    facility_id: FacilityId
    item_id: ItemId
    status: ForecastStatus
    forecast_at: datetime
    as_of: datetime
    inventory_record_id: str | None
    horizon_days: int
    min_cover_days: int
    starting_inventory: Units | None
    coverage_breach_day: Day | None
    coverage_breach_at: datetime | None
    stockout_day: Day | None
    stockout_at: datetime | None
    recovery_day: Day | None
    recovery_at: datetime | None
    projection: tuple[ProjectionRow, ...]
    drivers: tuple[str, ...]
    provenance: Provenance
    derived_from: DerivedFrom | None = None


class CareImpact(Frozen):
    facility_id: FacilityId
    item_id: ItemId
    status: ForecastStatus
    coverage_breach_day: Day | None
    recovery_day: Day | None
    scheduled_in_window: int
    exposed_event_ids: tuple[str, ...]
    exposed_obligation_ids: tuple[str, ...] = ()
    exposed_total: int | None = Field(description="null when the forecast cannot establish exposure")
    exposed_by_category: dict[CareCategory, int] | None
    exposed_units: Units | None
    unserved_event_ids: tuple[str, ...]
    unserved_obligation_ids: tuple[str, ...] = ()
    unserved_total: int | None
    derived_from: DerivedFrom | None = None

    @model_validator(mode="after")
    def _availability(self) -> "CareImpact":
        totals = (self.exposed_total, self.exposed_by_category, self.exposed_units, self.unserved_total)
        if self.status is ForecastStatus.UNAVAILABLE and any(value is not None for value in totals):
            raise ValueError("unavailable care impact cannot contain numeric exposure results")
        if self.status is ForecastStatus.FORECAST and any(value is None for value in totals):
            raise ValueError("available care impact requires numeric exposure results")
        return self


# ── proposals ───────────────────────────────────────────────────────────────


class CandidateChecks(Frozen):
    route_exists: bool
    donor_inventory_known: bool
    donor_not_already_at_risk: bool
    sufficient_transferable_stock: bool   # ≡ donor stays safe through its window after releasing q
    arrives_before_recipient_breach: bool
    recipient_recovers: bool


class BatchAllocation(Frozen):
    batch_id: str
    quantity: Units
    expires_at: datetime | None


class RankComponents(Frozen):
    """Lexicographic order: expiry relief → transit → post-transfer margin. No weights."""

    expiry_relief: bool
    transit_hours: Decimal
    post_transfer_margin: int


class InterventionCandidate(Frozen):
    id: str
    donor_id: FacilityId
    recipient_id: FacilityId
    item_id: ItemId
    quantity: Units
    donor_inventory: Units | None
    transferable: int
    donor_protection_window_days: int
    donor_coverage_breach_day: Day | None
    donor_post_transfer_breach_day: Day | None
    donor_post_transfer_margin: int
    distance_km: Decimal
    transit_hours: Decimal
    dispatch_ready_at: datetime
    expected_arrival_at: datetime
    arrival_day: Day
    recipient_breach_at: datetime | None
    recipient_post_transfer_breach_day: Day | None
    allocations: tuple[BatchAllocation, ...]
    expiry_relief: bool
    feasible: bool
    checks: CandidateChecks
    rejection_reasons: tuple[RejectionReason, ...]
    rank: int | None
    rank_components: RankComponents
    verdict: CandidateVerdict
    derived_from: DerivedFrom | None = None


class InterventionPlan(Frozen):
    id: str
    case_id: str
    recipient_id: FacilityId
    item_id: ItemId
    required_quantity: Units
    hold_through_day: Day
    chosen: InterventionCandidate | None
    candidates: tuple[InterventionCandidate, ...]
    evaluated_at: datetime
    invalidated: bool = False
    invalidation_reason: RejectionReason | None = None
    superseded_by_id: str | None = None
    derived_from: DerivedFrom | None = None


# ── workflow ────────────────────────────────────────────────────────────────


class EvidenceRecord(Frozen):
    id: str
    case_id: str
    facility_id: FacilityId
    item_id: ItemId
    observed_quantity: Units
    confidence: Decimal = Field(ge=0, le=1)
    source_type: SourceType
    captured_via: str
    observed_at: datetime
    state: EvidenceState
    canonical_quantity_at_submission: Units | None
    canonical_record_id_at_submission: str | None
    evidence_class: str = "USER_SUPPLIED_EVIDENCE"
    committed_record_id: str | None = None
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str = ""


class ExposureRef(Frozen):
    kind: ExposureKind
    id: str


class CareDeliveryRecord(Frozen):
    """Evidence that the exposed care obligation/event was actually delivered."""

    id: str
    case_id: str
    exposure: ExposureRef
    outcome: CareDeliveryOutcome
    verified_at: datetime
    verified_by: str
    source_ref: str
    provenance: Provenance
    note: str = ""


class VerificationRecord(Frozen):
    id: str
    case_id: str
    kind: VerificationKind
    expected: str
    observed: str | None
    outcome: VerificationOutcome
    verified_at: datetime
    verified_by: str
    note: str = ""


class ReconciliationRecord(Frozen):
    id: str
    case_id: str
    at: datetime
    outcome: ReconciliationOutcome
    originally_exposed_ids: tuple[str, ...]
    still_exposed_ids: tuple[str, ...]
    protected_count: int
    new_donor_record_id: str | None
    new_recipient_record_id: str | None
    note: str = ""
    originally_exposed_refs: tuple[ExposureRef, ...] = ()
    still_exposed_refs: tuple[ExposureRef, ...] = ()
    coverage_status: CoverageRecoveryStatus = CoverageRecoveryStatus.COVERAGE_NOT_RESTORED
    coverage_restored_count: int = 0


class AuditEvent(Frozen):
    seq: int
    at: datetime
    case_id: str | None
    action: str
    from_state: CaseState | None
    to_state: CaseState | None
    detail: dict[str, object] = Field(default_factory=dict)


class RecoveryCase(Frozen):
    id: str
    district_id: str
    recipient_id: FacilityId
    item_id: ItemId
    state: CaseState
    opened_at: datetime
    plan_id: str | None = None
    previous_plan_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    verification_ids: tuple[str, ...] = ()
    reconciliation_ids: tuple[str, ...] = ()
    originally_exposed_ids: tuple[str, ...] = ()
    originally_exposed_refs: tuple[ExposureRef, ...] = ()
    care_delivery_ids: tuple[str, ...] = ()
    transfer_supply_id: str | None = None
    care_protected_count: int | None = None
    closed_at: datetime | None = None
    applied_command_ids: tuple[str, ...] = ()
