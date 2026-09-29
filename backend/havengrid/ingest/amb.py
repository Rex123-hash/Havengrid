"""Parser for the public AMB rendered stock table.

The AMB dashboard reports district aggregates in lakhs. This adapter keeps the
aggregate as a `DistrictCommodityStockSignal`; it intentionally never emits an
`InventoryRecord` because no facility allocation is present in the source.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from ..domain.enums import Origin, ProvenanceStatus, SourceQualityFlag, SourceType
from ..domain.models import DistrictCommodityStockSignal, Provenance

MONTHS = ("April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March")


class AMBParseError(ValueError):
    pass


def source_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def parse_ifa_red_stock(payload: dict[str, Any], *, source_ref: str | None = None, source_hash_override: str | None = None) -> tuple[DistrictCommodityStockSignal, ...]:
    """Parse the captured AMB table into one signal per month."""
    table = payload.get("table")
    if not isinstance(table, dict) or table.get("columns", [])[2:] != list(MONTHS):
        raise AMBParseError("AMB table must contain the twelve named months")
    if payload.get("commodity") != "IFA Red":
        raise AMBParseError("capture is not the IFA Red commodity")
    rows = {str(r.get("indicator")): r.get("values") for r in table.get("rows", []) if isinstance(r, dict)}
    required = {
        "Stock balance from last month – IFA Red",
        "Stocks received – IFA Red",
        "Stocks unusable – IFA Red",
        "Stocks distributed – IFA Red",
        "Stocks available – IFA Red",
    }
    if set(rows) != required or any(not isinstance(v, list) or len(v) != 12 for v in rows.values()):
        raise AMBParseError("IFA Red capture is missing one or more monthly rows")
    digest = source_hash_override or source_hash(payload)
    as_of = payload.get("data_as_on")
    observed = datetime.fromisoformat(str(as_of)).replace(tzinfo=timezone.utc)
    retrieved_at = datetime.fromisoformat(str(payload.get("captured_at", as_of)).replace("Z", "+00:00"))
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    district = str(payload["district"]).lower()
    district_id = district.replace(" ", "-")
    periods = [f"{payload['financial_year']}:{month}" for month in MONTHS]
    out: list[DistrictCommodityStockSignal] = []
    for i, period in enumerate(periods):
        try:
            opening = Decimal(str(rows["Stock balance from last month – IFA Red"][i]))
            received = Decimal(str(rows["Stocks received – IFA Red"][i]))
            distributed = Decimal(str(rows["Stocks distributed – IFA Red"][i]))
            unusable = Decimal(str(rows["Stocks unusable – IFA Red"][i]))
            available = Decimal(str(rows["Stocks available – IFA Red"][i]))
        except Exception as e:
            raise AMBParseError(f"non-numeric value in month {MONTHS[i]}") from e
        if any(not x.is_finite() for x in (opening, received, distributed, unusable, available)):
            raise AMBParseError(f"non-finite stock value in month {MONTHS[i]}")
        flags: list[SourceQualityFlag] = []
        quality_note = "Rendered public AMB table; district aggregate only."
        if any(x < 0 for x in (opening, received, distributed, unusable, available)):
            flags.append(SourceQualityFlag.NEGATIVE_REPORTED_STOCK)
            quality_note += " Source data contains a negative reported value; retain as a quality flag and do not use as usable stock."
        if opening + received - distributed - unusable != available:
            flags.append(SourceQualityFlag.BALANCE_EQUATION_MISMATCH)
            quality_note += " Source balance equation does not reconcile exactly."
        out.append(DistrictCommodityStockSignal(
            id=f"amb-{district_id}-ifa-red-{i+1:02d}", district_id=district_id, item_id="ifa-red-60mg-500mcg", period=period,
            opening_balance=opening, received=received, distributed=distributed, unusable=unusable, available=available,
            unit="lakh dispensing units", geographic_granularity="district",
              source_ref=source_ref or str(payload.get("source_url", "")), source_hash=digest,
              retrieved_at=retrieved_at,
              quality_flags=tuple(flags),
              provenance=Provenance(source_type=SourceType.DISTRICT_STOCK_SIGNAL, status=ProvenanceStatus.OBSERVED,
                                  observed_at=observed, source_ref=source_ref or str(payload.get("source_url", "")),
                                  origin=Origin.OFFICIAL_PUBLIC_DATA, source_period=str(payload["financial_year"]),
                                  retrieved_at=retrieved_at, geographic_granularity="district", source_hash=digest,
                                  publisher="Anemia Mukt Bharat / National Health Mission", note=quality_note,
                                  quality_flags=tuple(flags)),
        ))
    return tuple(out)


def load_ifa_red_stock(path: str | Path) -> tuple[DistrictCommodityStockSignal, ...]:
    p = Path(path)
    return parse_ifa_red_stock(json.loads(p.read_text(encoding="utf-8")), source_ref=str(p),
                               source_hash_override=hashlib.sha256(p.read_bytes()).hexdigest())
