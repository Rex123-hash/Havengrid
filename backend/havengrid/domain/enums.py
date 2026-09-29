"""Value vocabularies. Every important domain state is an enum, never a bare string.

Revised at the Phase 0A gate: cover-based coverage semantics, four-valued
verification, explicit synthetic origin, and no externally-callable
"assert care protected".
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Python 3.11+ has enum.StrEnum; this shim keeps 3.12+ compatibility explicit."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class FacilityTier(StrEnum):
    WAREHOUSE = "warehouse"
    CHC = "chc"
    PHC = "phc"


class Origin(StrEnum):
    """WHERE THIS NUMBER ACTUALLY CAME FROM — independent of `source_type` (what kind
    of record it semantically is).

        source_type = DIGITAL_LEDGER   origin = OFFICIAL_SYSTEM_EXPORT   → a real HMIS export
        source_type = FIELD_REGISTER   origin = USER_SUPPLIED_EVIDENCE   → a photo someone uploaded
        source_type = DIGITAL_LEDGER   origin = SYNTHETIC_TEST           → the Sundargarh test fixture

    The environment guard refuses to serve SYNTHETIC_TEST as operational truth
    outside development and test.
    """

    SYNTHETIC_TEST = "synthetic_test"                    # invented for tests / demos labelled synthetic
    OFFICIAL_PUBLIC_DATA = "official_public_data"        # published government / public dataset
    OFFICIAL_SYSTEM_EXPORT = "official_system_export"    # export from an operational system (HMIS, e-aushadhi…)
    USER_SUPPLIED_EVIDENCE = "user_supplied_evidence"    # a human submitted it (photo, count, confirmation)
    LIVE_EXTERNAL_API = "live_external_api"              # fetched from a live third-party service
    MODEL_DERIVED = "model_derived"                      # computed by the kernel / a model from other records
    SIMULATED_COUNTERFACTUAL = "simulated_counterfactual" # a what-if the system constructed and never observed


SYNTHETIC_ORIGINS = frozenset({Origin.SYNTHETIC_TEST})
OBSERVATIONAL_ORIGINS = frozenset({Origin.OFFICIAL_PUBLIC_DATA, Origin.OFFICIAL_SYSTEM_EXPORT, Origin.USER_SUPPLIED_EVIDENCE, Origin.LIVE_EXTERNAL_API})


class SourceType(StrEnum):
    """Semantic kind of source — what a real record of this type would be."""

    DIGITAL_LEDGER = "digital_ledger"        # facility stock ledger / HMIS
    FIELD_REGISTER = "field_register"        # photographed / transcribed paper register
    PHYSICAL_COUNT = "physical_count"        # a human counted the shelf
    SCHEDULED_INDENT = "scheduled_indent"    # routine planned distribution
    INTERVENTION = "intervention"            # emergency transfer created by this system
    DISTRICT_POLICY = "district_policy"      # configured policy value
    CARE_SCHEDULE = "care_schedule"          # appointment schedule
    CONSUMPTION_HISTORY = "consumption_history"
    KERNEL = "kernel"                        # produced by deterministic computation
    DISTRICT_STOCK_SIGNAL = "district_stock_signal"  # district-level context, not facility inventory
    PROGRAMME_ACTIVITY = "programme_activity"        # aggregated service activity
    FACILITY_DIRECTORY = "facility_directory"        # official facility metadata
    ROUTE_ESTIMATE = "route_estimate"                # travel-time provider response


class ProvenanceStatus(StrEnum):
    OBSERVED = "observed"
    REPORTED = "reported"
    INFERRED = "inferred"
    PREDICTED = "predicted"
    PROPOSED = "proposed"
    VERIFIED = "verified"


class ForecastStatus(StrEnum):
    FORECAST = "forecast"
    UNAVAILABLE = "unavailable"


class CareCategory(StrEnum):
    PAEDIATRIC = "paediatric"
    MATERNAL = "maternal"
    SCHEDULED = "scheduled"


class IncomingSupplyState(StrEnum):
    SCHEDULED = "scheduled"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class EvidenceState(StrEnum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class CandidateVerdict(StrEnum):
    """OUTPUT ONLY. A fixture must never carry one of these."""

    CHOSEN = "chosen"
    HELD = "held"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    NO_VALID_ROUTE = "NO_VALID_ROUTE"
    DONOR_IS_RECIPIENT = "DONOR_IS_RECIPIENT"
    DONOR_INVENTORY_UNKNOWN = "DONOR_INVENTORY_UNKNOWN"
    DONOR_ALREADY_AT_RISK = "DONOR_ALREADY_AT_RISK"          # donor breaches inside its window at q = 0
    INSUFFICIENT_TRANSFERABLE_STOCK = "INSUFFICIENT_TRANSFERABLE_STOCK"  # q > transferable (≡ unsafe after transfer)
    ARRIVES_AFTER_RECIPIENT_BREACH = "ARRIVES_AFTER_RECIPIENT_BREACH"
    RECIPIENT_NOT_RECOVERED = "RECIPIENT_NOT_RECOVERED"
    INVALIDATED_BY_CONFIRMED_EVIDENCE = "INVALIDATED_BY_CONFIRMED_EVIDENCE"
    FACILITY_UNVERIFIED = "FACILITY_UNVERIFIED"


class CaseState(StrEnum):
    FORECASTED = "FORECASTED"
    INTERVENTION_PROPOSED = "INTERVENTION_PROPOSED"
    AWAITING_EVIDENCE_CONFIRMATION = "AWAITING_EVIDENCE_CONFIRMATION"
    EVIDENCE_CONFIRMED = "EVIDENCE_CONFIRMED"
    PLAN_INVALIDATED = "PLAN_INVALIDATED"
    PLAN_RECALCULATED = "PLAN_RECALCULATED"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    DESTINATION_VERIFIED = "DESTINATION_VERIFIED"
    BATCH_MATCHED = "BATCH_MATCHED"
    COVERAGE_RESTORED = "COVERAGE_RESTORED"
    CARE_PROTECTED = "CARE_PROTECTED"
    CLOSED = "CLOSED"


class CaseAction(StrEnum):
    """Commands. Those marked (system) are issued by the service, never by the API."""

    PROPOSE = "propose"
    SUBMIT_EVIDENCE = "submit_evidence"
    CONFIRM_EVIDENCE = "confirm_evidence"
    REJECT_EVIDENCE = "reject_evidence"
    PLAN_STILL_VALID = "plan_still_valid"       # (system)
    INVALIDATE_PLAN = "invalidate_plan"         # (system)
    RECALCULATE_PLAN = "recalculate_plan"       # (system)
    APPROVE = "approve"
    DISPATCH = "dispatch"
    VERIFY_SOURCE = "verify_source"
    VERIFY_DESTINATION = "verify_destination"
    VERIFY_BATCH = "verify_batch"
    RECONCILE = "reconcile"                     # computes; cannot assert an outcome
    CARE_DELIVERY = "care_delivery"             # dedicated delivery verification endpoint
    CLOSE = "close"


SYSTEM_ACTIONS = frozenset({CaseAction.PLAN_STILL_VALID, CaseAction.INVALIDATE_PLAN, CaseAction.RECALCULATE_PLAN})


class VerificationKind(StrEnum):
    SOURCE = "source"
    DESTINATION = "destination"
    BATCH = "batch"


class VerificationOutcome(StrEnum):
    """UNKNOWN is neither success nor failure and never advances a case."""

    VERIFIED = "verified"
    NOT_APPLIED = "not_applied"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class ReconciliationOutcome(StrEnum):
    COVERAGE_RESTORED = "coverage_restored"
    CARE_PROTECTED = "care_protected"
    STILL_EXPOSED = "still_exposed"
    NOT_READY = "not_ready"


class ExposureKind(StrEnum):
    CARE_EVENT = "care_event"
    CARE_OBLIGATION = "care_obligation"


class CareDeliveryOutcome(StrEnum):
    DELIVERED = "delivered"
    DEFERRED = "deferred"
    NOT_DELIVERED = "not_delivered"
    UNKNOWN = "unknown"


class CoverageRecoveryStatus(StrEnum):
    COVERAGE_RESTORED = "coverage_restored"
    COVERAGE_NOT_RESTORED = "coverage_not_restored"


class EvidenceGrade(StrEnum):
    DIRECTLY_LINKED = "directly_linked"
    PROGRAMME_ESTIMATED = "programme_estimated"
    NOT_SUPPORTED = "not_supported"


class CurrentnessStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"
    CURRENT_VERIFIED = "current_verified"
    HISTORICAL_CORROBORATED = "historical_corroborated"
    UNVERIFIED = "unverified"


class ReadinessStatus(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class FacilityInventoryStatus(StrEnum):
    AVAILABLE = "available"
    INVENTORY_REQUIRED = "inventory_required"
    SOURCE_STALE = "source_stale"


class SourceQualityFlag(StrEnum):
    """A quality condition attached to an observed source value.

    Flags are additive diagnostics.  They never rewrite the source value and a
    flagged aggregate cannot silently become facility inventory or donor truth.
    """

    NEGATIVE_REPORTED_STOCK = "NEGATIVE_REPORTED_STOCK"
    BALANCE_EQUATION_MISMATCH = "BALANCE_EQUATION_MISMATCH"
    MISSING_MONTH = "MISSING_MONTH"
    STALE_PERIOD = "STALE_PERIOD"
    IMPOSSIBLE_PERCENTAGE = "IMPOSSIBLE_PERCENTAGE"
    UNIT_AMBIGUOUS = "UNIT_AMBIGUOUS"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class RouteObservationStatus(StrEnum):
    OK = "OK"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
