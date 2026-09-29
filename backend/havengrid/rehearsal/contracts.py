"""Machine-readable contract for the future cinematic UI migration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.models import validate_retrieved_at


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactClass(str, Enum):
    REAL_PUBLIC = "REAL_PUBLIC"
    LIVE_EXTERNAL_API = "LIVE_EXTERNAL_API"
    REHEARSAL_EVIDENCE = "REHEARSAL_EVIDENCE"
    REHEARSAL_ASSUMPTION = "REHEARSAL_ASSUMPTION"
    MODEL_DERIVED = "MODEL_DERIVED"
    UNKNOWN = "UNKNOWN"


class NumberRange(ContractModel):
    low: Decimal
    high: Decimal
    unit: str


class RouteFact(ContractModel):
    donor_id: str
    recipient_id: str
    distance_km: Decimal | None
    duration_hours: Decimal | None
    static_duration_hours: Decimal | None
    retrieved_at: datetime
    provider: str
    request_hash: str
    status: str
    provenance: dict[str, Any]

    @model_validator(mode="after")
    def _retrieved_not_in_future(self) -> "RouteFact":
        validate_retrieved_at(self.retrieved_at)
        return self


class DonorFact(ContractModel):
    donor_id: str
    donor_name: str
    feasible: bool
    rank: int | None
    verdict: str
    quantity: int
    rejection_reasons: list[str]
    route: RouteFact | None
    donor_inventory: int | None
    transferable: int
    post_transfer_margin: int
    expiry_relief: bool


class JudgeScenarioContract(ContractModel):
    """All facts a UI may display for one rehearsal run.

    The frontend consumes this object; it must not recompute forecast, exposure,
    transfer sizing, ranking, or recovery claims from source rows.
    """

    schema_version: str = "0.8.1"
    scenario_id: str
    mode: str = "rehearsal"
    rehearsal_label: str
    district: dict[str, Any]
    recipient_facility: dict[str, Any]
    commodity: dict[str, Any]
    district_public_stock_context: dict[str, Any]
    stock_source_date: str
    facility_observation: dict[str, Any]
    programme_obligation: dict[str, Any]
    forecast: dict[str, Any]
    programme_demand: int
    baseline_demand: dict[str, Any]
    coverage_breach_day: int | None
    stockout_day: int | None
    exposure_range: NumberRange
    transfer_quantity: int
    transfer_quantity_unit: str
    physical_dispatch_unit: str
    transfer_quantity_note: str
    initial_donor_candidates: list[DonorFact]
    donor_candidates: list[DonorFact]
    initial_chosen_donor: str | None
    evidence_correction: dict[str, Any]
    replanned_donor: str | None
    coverage_recovery: dict[str, Any]
    care_delivery_verification: dict[str, Any]
    lifecycle: list[str]
    provenance_labels: dict[str, str]
    fact_classifications: dict[str, FactClass]
    derived_from: dict[str, list[str]]
    assumption_notes: dict[str, str]
    unknown_facts: list[str]
    generated_at: datetime

    def classification_for(self, path: str) -> FactClass:
        """Resolve the most specific explicit path; parents cover descendants."""
        matches = [key for key in self.fact_classifications
                   if path == key or path.startswith(key + ".")]
        if not matches:
            raise ValueError(f"Unclassified displayed fact: {path}")
        return self.fact_classifications[max(matches, key=len)]

    @model_validator(mode="after")
    def _fact_classification_contract(self) -> "JudgeScenarioContract":
        metadata = {"fact_classifications", "derived_from", "assumption_notes", "provenance_labels"}
        for name in type(self).model_fields:
            if name not in metadata:
                self.classification_for(name)
        allowed = set(FactClass)
        if any(value not in allowed for value in self.fact_classifications.values()):
            raise ValueError("fact_classifications contains an unsupported class")
        for path, fact_class in self.fact_classifications.items():
            if fact_class is FactClass.MODEL_DERIVED and not self.derived_from.get(path):
                raise ValueError(f"MODEL_DERIVED fact '{path}' requires derived_from")
            if fact_class is FactClass.REHEARSAL_ASSUMPTION and not self.assumption_notes.get(path):
                raise ValueError(f"REHEARSAL_ASSUMPTION fact '{path}' requires an assumption note")
        return self
