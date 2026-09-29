"""Sundargarh's first official-data slice (AMB district context)."""

from __future__ import annotations

from pathlib import Path
from decimal import Decimal

from ..domain.enums import EvidenceGrade
from ..domain.models import IFADoseRule, Item, UnitsRule
from ..ingest.amb import load_ifa_red_stock
from ..profiles import sundargarh_profile

ITEM_ID = "ifa-red-60mg-500mcg"
RAW_STOCK = Path(__file__).resolve().parents[3] / "data" / "raw" / "official" / "amb" / "sundargarh-ifa-stock-2025-2026.json"


def ifa_red_item() -> Item:
    basis = "https://nhm.gov.in/images/pdf/Nutrition/AMB-guidelines/Anemia-Mukt-Bharat-Operational-Guidelines-FINAL.pdf"
    return Item(
        id=ITEM_ID,
        name="IFA Red",
        form="60 mg elemental iron + 500 µg folic acid",
        unit="dispensing unit",
        pack_size=1,  # calculation granularity only; physical pack size is not public
        physical_dispatch_unit="UNKNOWN",
        units_rule=UnitsRule(
            id="ifa-red-pregnancy-180-day-course",
            description="one red IFA tablet per day for the AMB pregnancy/postpartum course",
            numerator="tablets",
            denominator="person-day",
            units_per_person=Decimal("1"),
            source_ref="https://www.nhm.gov.in/digigov-portal/index1.php?lang=1&level=3&lid=797&sublinkid=1448",
            evidence_grade=EvidenceGrade.DIRECTLY_LINKED,
        ),
        dose_rules=(
            IFADoseRule(id="ifa-red-antenatal", quantity=Decimal("1"), unit="tablet", frequency="daily",
                        population="pregnant women", programme_phase="antenatal: from the fourth month / second trimester; minimum 180 days during pregnancy",
                        duration_days=180, basis_ref=basis, evidence_grade=EvidenceGrade.DIRECTLY_LINKED),
            IFADoseRule(id="ifa-red-postpartum", quantity=Decimal("1"), unit="tablet", frequency="daily",
                        population="lactating mothers with a 0–6 month child", programme_phase="postpartum continuation after delivery",
                        duration_days=180, basis_ref=basis, evidence_grade=EvidenceGrade.DIRECTLY_LINKED),
        ),
    )


def sundargarh_ifa_slice():
    """Return profile, item, and district stock signals; no facility inventory."""
    signals = load_ifa_red_stock(RAW_STOCK)
    public_ref = "https://www.anemiamuktbharat.info/reports/stock"
    signals = tuple(x.model_copy(update={"source_ref": public_ref, "provenance": x.provenance.model_copy(update={"source_ref": public_ref})}) for x in signals)
    return sundargarh_profile(), ifa_red_item(), signals
