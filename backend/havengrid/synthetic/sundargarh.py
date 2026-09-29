"""The Sundargarh demonstration district (approved at the Phase 0A gate).

FACTS AND POLICIES ONLY. This file contains no breach day, no exposed count,
no chosen donor, no transfer quantity, no resulting breach, no protected count.
Every one of those is produced by the kernel from what is here.

Every record is `origin = SYNTHETIC_TEST`. Nothing here is connected to a real
HMIS, register, warehouse or facility.

Synthetic world, in one paragraph
    It is Monday 14 September 2026, 08:00 IST (T0 = 02:30 UTC). Odisha is in
    its post-monsoon paediatric infection season, so amoxicillin suspension is
    dispensing above its annual average district-wide. Bhatpar PHC ran a
    paediatric outreach camp a week ago; its second-dose follow-ups fall on
    days 7–12. Its fortnightly indent (200 bottles) is due in 13 days. CHC D
    holds a batch that expires on day 21 and has not physically counted its
    shelf for nine days.

    SYNTHETIC ASSUMPTION (test-only, not a clinical claim): one dispensing unit
    = one bottle, and each care encounter consumes one unit. Real sources must
    supply `units_per_attendance` with a cited basis (EDL / STG / policy).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..domain.enums import CareCategory, CaseState, CurrentnessStatus, FacilityTier, IncomingSupplyState, Origin, ProvenanceStatus, SourceType
from ..domain.models import (
    Batch,
    CareEvent,
    CoverPolicy,
    DemandProfile,
    District,
    Facility,
    IncomingSupply,
    InventoryRecord,
    Item,
    Provenance,
    RecoveryCase,
    Route,
    SchematicPosition,
    SupplyLink,
)
from ..store import ScenarioState

T0 = datetime(2026, 9, 14, 2, 30, tzinfo=timezone.utc)   # 08:00 IST Monday
DAY = timedelta(hours=24)
ITEM = "amoxicillin-susp-125"
CASE_ID = "case-bhatpar-amox-001"


def _p(source_type: SourceType, status: ProvenanceStatus, observed_at: datetime, ref: str, *, confidence: str = "1", note: str = "") -> Provenance:
    return Provenance(source_type=source_type, status=status, observed_at=observed_at, source_ref=ref,
                      origin=Origin.SYNTHETIC_TEST, confidence=Decimal(confidence), note=note)


def day_at(day: int, offset_hours: float = 0) -> datetime:
    """Timestamp inside bucket `day`: bucket start (08:00 IST) plus `offset_hours`."""
    return T0 + DAY * (day - 1) + timedelta(hours=offset_hours)


def build_sundargarh() -> ScenarioState:
    policy = CoverPolicy(
        min_cover_days=3,          # ≈ 2× the ~1-day peer-transfer lead time in this district, plus one day margin
        planning_window_days=14,   # PHC fortnightly indent cycle
        horizon_days=30,
        dispatch_lead_hours={FacilityTier.PHC: Decimal("2"), FacilityTier.CHC: Decimal("2"), FacilityTier.WAREHOUSE: Decimal("24")},
        havengrid_continuity_threshold_days=3,
        provenance=_p(SourceType.DISTRICT_POLICY, ProvenanceStatus.OBSERVED, T0, "district-policy/2026-q3",
                      note="cover-based thresholds; no fixed reserve numbers"),
    )
    district = District(id="sundargarh", name="Sundargarh", region="Odisha", timezone="Asia/Kolkata", forecast_at=T0, policy=policy)
    st = ScenarioState(district=district)

    # Unit is a generic dispensing unit. The synthetic mapping "1 unit = 1 bottle, 1
    # encounter = 1 unit" is a TEST assumption, not a clinical claim (see module doc).
    st.items[ITEM] = Item(id=ITEM, name="Amoxicillin", form="oral suspension · 125 mg / 5 ml", unit="dispensing unit", pack_size=10, physical_dispatch_unit="bottle")

    def fac(id_: str, name: str, short: str, tier: FacilityTier, x: int, y: int) -> None:
        st.facilities[id_] = Facility(id=id_, name=name, short_name=short, tier=tier, district_id="sundargarh", position=SchematicPosition(x=x, y=y),
                                      currentness=CurrentnessStatus.CURRENT_VERIFIED, coordinate_source="synthetic schematic")

    fac("warehouse", "District Warehouse", "Warehouse", FacilityTier.WAREHOUSE, 498, 78)
    fac("chc-a", "CHC A · Talsara", "CHC A", FacilityTier.CHC, 330, 182)
    fac("chc-b", "CHC B · Hemgir", "CHC B", FacilityTier.CHC, 636, 172)
    fac("chc-c", "CHC C · Bonai", "CHC C", FacilityTier.CHC, 188, 308)
    fac("chc-d", "CHC D · Kuchinda", "CHC D", FacilityTier.CHC, 762, 338)
    fac("koira", "Koira PHC", "Koira", FacilityTier.PHC, 252, 108)
    fac("kansbahal", "Kansbahal PHC", "Kansbahal", FacilityTier.PHC, 118, 196)
    fac("bargaon", "Bargaon PHC", "Bargaon", FacilityTier.PHC, 848, 108)
    fac("kutra", "Kutra PHC", "Kutra", FacilityTier.PHC, 402, 262)
    fac("lahunipada", "Lahunipada PHC", "Lahunipada", FacilityTier.PHC, 250, 408)
    fac("tileibani", "Tileibani PHC", "Tileibani", FacilityTier.PHC, 142, 462)
    fac("bhatpar", "Bhatpar PHC", "Bhatpar", FacilityTier.PHC, 500, 362)
    fac("nuagaon", "Nuagaon PHC", "Nuagaon", FacilityTier.PHC, 866, 232)
    fac("remed", "Remed PHC", "Remed", FacilityTier.PHC, 858, 438)

    for a, b in [("warehouse", "chc-a"), ("warehouse", "chc-b"), ("warehouse", "chc-c"), ("warehouse", "chc-d"),
                 ("chc-a", "koira"), ("chc-a", "kansbahal"), ("chc-a", "kutra"), ("chc-b", "bargaon"), ("chc-b", "nuagaon"),
                 ("chc-b", "bhatpar"), ("chc-c", "tileibani"), ("chc-c", "lahunipada"), ("chc-d", "remed"), ("chc-d", "bhatpar")]:
        st.links.append(SupplyLink(from_id=a, to_id=b))

    # Emergency-transfer routes into Bhatpar (district road table).
    for src, km, hrs in [("chc-d", "42", "1.5"), ("chc-b", "68", "2.6"), ("kansbahal", "31", "1.1"), ("lahunipada", "27", "1.0"), ("warehouse", "96", "144")]:
        st.routes[(src, "bhatpar")] = Route(from_id=src, to_id="bhatpar", distance_km=Decimal(km), transit_hours=Decimal(hrs),
                                            provenance=_p(SourceType.DISTRICT_POLICY, ProvenanceStatus.OBSERVED, T0, "district-road-table/2026",
                                                          note="warehouse: weekly truck slot + travel"))

    def inv(id_: str, facility: str, qty: int, *, counted_days_ago: int, note: str = "") -> None:
        st.inventory[id_] = InventoryRecord(
            id=id_, facility_id=facility, item_id=ITEM, quantity=qty, canonical=True,
            provenance=_p(SourceType.DIGITAL_LEDGER, ProvenanceStatus.REPORTED, T0, f"ledger/{facility}",
                          note=note or f"last physical count {counted_days_ago} days before T0"),
        )

    def demand(facility: str, daily: list[int], shape: str) -> None:
        st.demand[(facility, ITEM)] = DemandProfile(facility_id=facility, item_id=ITEM, daily=tuple(daily), shape_note=shape,
                                                     provenance=_p(SourceType.CONSUMPTION_HISTORY, ProvenanceStatus.INFERRED, T0, f"consumption-history/{facility}/90d"))

    def supply(id_: str, dest: str, qty: int, day: int, *, source: str | None = None) -> None:
        st.supplies[id_] = IncomingSupply(id=id_, destination_id=dest, source_id=source, item_id=ITEM, quantity=qty,
                                          expected_arrival_at=day_at(day), state=IncomingSupplyState.SCHEDULED,
                                          provenance=_p(SourceType.SCHEDULED_INDENT, ProvenanceStatus.REPORTED, T0, f"indent/{dest}"))

    def batch(id_: str, facility: str, qty: int, expires: datetime | None) -> None:
        st.batches[id_] = Batch(id=id_, facility_id=facility, item_id=ITEM, quantity=qty, expires_at=expires,
                                provenance=_p(SourceType.DIGITAL_LEDGER, ProvenanceStatus.REPORTED, T0, f"batch-register/{facility}"))

    events: list[CareEvent] = []

    def event(facility: str, cat: CareCategory, day: int, n: int, desc: str, offset_hours: float = 2) -> None:
        # 10:00 IST clinic slot = bucket start + 2 h
        for _ in range(n):
            i = len(events) + 1
            events.append(CareEvent(id=f"ce-{facility}-{i:03d}", facility_id=facility, category=cat, scheduled_at=day_at(day, offset_hours),
                                    item_id=ITEM, units_required=1, description=desc,
                                    provenance=_p(SourceType.CARE_SCHEDULE, ProvenanceStatus.REPORTED, T0, f"care-schedule/{facility}")))

    # ── Bhatpar PHC — the recipient ──────────────────────────────────────
    inv("inv-bhatpar-001", "bhatpar", 143, counted_days_ago=3)
    demand("bhatpar", [12] * 14, "flat 12/day — high-OPD PHC in post-monsoon paediatric season")
    supply("sup-bhatpar-indent-001", "bhatpar", 200, 14, source="chc-b")   # fortnightly indent, 13 days out → bucket 14
    for d, n in [(7, 2), (8, 2), (9, 2), (10, 2), (11, 2), (12, 1)]:
        event("bhatpar", CareCategory.PAEDIATRIC, d, n, "second-dose follow-up from outreach camp (day −7)")
    for d, n in [(2, 2), (4, 1), (9, 2), (11, 2)]:
        event("bhatpar", CareCategory.MATERNAL, d, n, "ANC/PNC clinic (Tue/Thu) with prescribed course")
    for d in [3, 6, 8, 10, 13]:
        event("bhatpar", CareCategory.SCHEDULED, d, 1, "routine outpatient review")

    # ── CHC D · Kuchinda — initial donor; stale physical count ───────────
    inv("inv-chc-d-001", "chc-d", 286, counted_days_ago=9, note="last physical count 9 days before T0 — ledger not reconciled since")
    demand("chc-d", [8] * 14, "flat 8/day — CHC referral load for suspension")
    supply("sup-chc-d-indent-001", "chc-d", 250, 21, source="warehouse")
    batch("AMX-2401-K", "chc-d", 90, day_at(21))          # expires inside the horizon → expiry pressure
    batch("AMX-2402-M", "chc-d", 196, datetime(2027, 3, 31, tzinfo=timezone.utc))
    for d in range(1, 15):
        event("chc-d", CareCategory.PAEDIATRIC, d, 1, "daily paediatric OPD review")

    # ── CHC B · Hemgir ───────────────────────────────────────────────────
    inv("inv-chc-b-001", "chc-b", 340, counted_days_ago=1)
    demand("chc-b", [7] * 14, "flat 7/day")
    supply("sup-chc-b-indent-001", "chc-b", 300, 18, source="warehouse")
    batch("AMX-2403-B", "chc-b", 200, datetime(2027, 1, 31, tzinfo=timezone.utc))
    batch("AMX-2404-C", "chc-b", 140, datetime(2027, 2, 28, tzinfo=timezone.utc))
    for d in [2, 5, 7, 9, 12, 14]:
        event("chc-b", CareCategory.SCHEDULED, d, 1, "scheduled review")

    # ── Kansbahal PHC — busy, already thin ───────────────────────────────
    inv("inv-kansbahal-001", "kansbahal", 150, counted_days_ago=2)
    demand("kansbahal", [14] * 14, "flat 14/day — busiest PHC OPD in the block")
    supply("sup-kansbahal-indent-001", "kansbahal", 200, 10, source="chc-a")
    for d in range(1, 15):
        event("kansbahal", CareCategory.PAEDIATRIC, d, 1, "paediatric OPD")
    for d in [3, 7, 11]:
        event("kansbahal", CareCategory.MATERNAL, d, 1, "PNC visit")

    # ── Lahunipada PHC — small, quiet ────────────────────────────────────
    inv("inv-lahunipada-001", "lahunipada", 60, counted_days_ago=5)
    demand("lahunipada", [2] * 14, "flat 2/day — small PHC")
    supply("sup-lahunipada-indent-001", "lahunipada", 100, 20, source="chc-c")
    for d in [2, 4, 6, 8, 10, 12]:
        event("lahunipada", CareCategory.SCHEDULED, d, 1, "scheduled review")

    # ── District Warehouse ───────────────────────────────────────────────
    inv("inv-warehouse-001", "warehouse", 1440, counted_days_ago=1)
    demand("warehouse", [20] * 14, "flat 20/day issued to CHCs")
    batch("AMX-2405-W", "warehouse", 1440, datetime(2027, 6, 30, tzinfo=timezone.utc))

    # ── Other facilities (no route into Bhatpar; forecast for the network view) ──
    inv("inv-nuagaon-001", "nuagaon", 190, counted_days_ago=4); demand("nuagaon", [13] * 14, "flat 13/day")
    supply("sup-nuagaon-indent-001", "nuagaon", 180, 16, source="chc-b")
    for d in [1, 2, 4, 5, 6, 7, 8, 10, 11, 13, 14]:
        event("nuagaon", CareCategory.PAEDIATRIC, d, 1, "paediatric OPD")
    inv("inv-remed-001", "remed", 300, counted_days_ago=2, note="indent received 2 days before T0"); demand("remed", [8] * 14, "flat 8/day")
    for d in [1, 3, 5, 7, 8, 10, 12, 13, 14]:
        event("remed", CareCategory.SCHEDULED, d, 1, "scheduled review")
    inv("inv-koira-001", "koira", 220, counted_days_ago=3); demand("koira", [6] * 14, "flat 6/day")
    inv("inv-bargaon-001", "bargaon", 200, counted_days_ago=2); demand("bargaon", [5] * 14, "flat 5/day")
    inv("inv-tileibani-001", "tileibani", 180, counted_days_ago=3); demand("tileibani", [5] * 14, "flat 5/day")
    inv("inv-chc-a-001", "chc-a", 400, counted_days_ago=2); demand("chc-a", [9] * 14, "flat 9/day")
    inv("inv-chc-c-001", "chc-c", 380, counted_days_ago=4); demand("chc-c", [8] * 14, "flat 8/day")
    # Kutra: NO canonical inventory. Ledger flagged unreliable; last count 16 days ago.
    demand("kutra", [6] * 14, "flat 6/day")

    for e in events:
        st.care_events[e.id] = e

    st.cases[CASE_ID] = RecoveryCase(id=CASE_ID, district_id="sundargarh", recipient_id="bhatpar", item_id=ITEM,
                                     state=CaseState.FORECASTED, opened_at=T0)
    return st
