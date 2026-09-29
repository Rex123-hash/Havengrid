"""Strict normalisation boundary for AMB/HMIS programme activity rows."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ..domain.enums import EvidenceGrade, Origin, ProvenanceStatus, SourceQualityFlag, SourceType
from ..domain.models import ProgrammeActivity, Provenance


class ActivityParseError(ValueError):
    pass


def parse_programme_activity(row: dict[str, Any], *, source_ref: str, source_hash: str | None = None) -> ProgrammeActivity:
    required = ("district_id", "period", "indicator", "unit", "evidence_grade", "basis", "retrieved_at")
    missing = [k for k in required if k not in row]
    if missing:
        raise ActivityParseError(f"missing activity fields: {', '.join(missing)}")
    try:
        grade = EvidenceGrade(str(row["evidence_grade"]))
    except ValueError as e:
        raise ActivityParseError("unknown evidence_grade") from e
    value = row.get("value")
    if grade is EvidenceGrade.NOT_SUPPORTED and value is not None:
        raise ActivityParseError("NOT_SUPPORTED activity cannot carry a value")
    if grade is EvidenceGrade.PROGRAMME_ESTIMATED and not all(row.get(k) is not None for k in ("allocation_method", "uncertainty", "derived_from")):
        raise ActivityParseError("PROGRAMME_ESTIMATED activity requires explicit allocation and uncertainty")
    try:
        retrieved = datetime.fromisoformat(str(row["retrieved_at"]).replace("Z", "+00:00"))
    except ValueError as e:
        raise ActivityParseError("retrieved_at must be an ISO timestamp") from e
    if retrieved.tzinfo is None:
        retrieved = retrieved.replace(tzinfo=timezone.utc)
    observed_at = datetime.fromisoformat(str(row.get("observed_at", row["retrieved_at"])).replace("Z", "+00:00"))
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    flags: list[SourceQualityFlag] = []
    if value is not None and str(row["unit"]).lower() in {"percent", "%", "percentage"}:
        if Decimal(str(value)) < 0 or Decimal(str(value)) > 100:
            flags.append(SourceQualityFlag.IMPOSSIBLE_PERCENTAGE)
    if not str(row["unit"]).strip() or str(row["unit"]).lower() in {"unknown", "n/a", "na"}:
        flags.append(SourceQualityFlag.UNIT_AMBIGUOUS)
    return ProgrammeActivity(
        id=str(row.get("id", f"{row['district_id']}:{row['period']}:{row['indicator']}")), district_id=str(row["district_id"]),
        period=str(row["period"]), indicator=str(row["indicator"]), value=None if value is None else Decimal(str(value)),
        unit=str(row["unit"]), evidence_grade=grade, basis=str(row.get("basis", "")),
        allocation_method=row.get("allocation_method"), uncertainty=None if row.get("uncertainty") is None else Decimal(str(row["uncertainty"])),
        derived_from=tuple(str(x) for x in (row.get("derived_from") or ())),
        provenance=Provenance(source_type=SourceType.PROGRAMME_ACTIVITY, status=ProvenanceStatus.OBSERVED,
                              observed_at=observed_at, source_ref=source_ref, origin=Origin.OFFICIAL_PUBLIC_DATA,
                              source_period=str(row["period"]), retrieved_at=retrieved, geographic_granularity="district",
                              source_hash=source_hash, publisher="Anemia Mukt Bharat / HMIS", note=f"retrieved_at={retrieved.isoformat()}",
                              quality_flags=tuple(flags)),
    )
