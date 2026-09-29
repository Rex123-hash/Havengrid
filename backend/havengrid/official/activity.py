"""Captured AMB KPI activity for the Sundargarh rehearsal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..domain.enums import EvidenceGrade
from ..ingest.activity import parse_programme_activity

CAPTURE = Path(__file__).resolve().parents[3] / "data" / "raw" / "official" / "amb" / "sundargarh-kpi-2025-05.json"
KPI_URL = "https://stage-api-test.anemiamuktbharat.info/report/kpiMonthly"


def load_sundargarh_kpi_activity():
    payload = json.loads(CAPTURE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
    rows = []
    for key, indicator in (
        ("pregnant_women_given_180_ifa_percent", "HMIS 1.2.4: pregnant women given 180 IFA tablets"),
        ("lactating_mothers_given_180_ifa_percent", "AMB KPI: lactating mothers given full 180-tablet IFA course"),
    ):
        rows.append(parse_programme_activity({
            "id": f"amb-kpi-sundargarh-may-2025-{key}", "district_id": "sundargarh", "period": "2025-2026:May",
            "indicator": indicator, "value": payload["indicators"][key], "unit": "percent",
            "evidence_grade": EvidenceGrade.DIRECTLY_LINKED.value,
            "basis": "Captured AMB KPI monthly response; the KPI is a district percentage and carries no facility denominator.",
            "observed_at": payload["data_as_on"], "retrieved_at": payload["retrieved_at"],
        }, source_ref=KPI_URL, source_hash=digest))
    return tuple(rows)
