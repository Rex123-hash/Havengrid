"""Permanent regression for timestamp/bucket semantics.

We previously shipped a helper whose docstring said "UTC hour" while its
argument was an offset from bucket start. These tests pin the contract.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from havengrid.synthetic.sundargarh import DAY, T0, build_sundargarh, day_at

IST = ZoneInfo("Asia/Kolkata")


def test_t0_is_08_00_ist_monday():
    local = T0.astimezone(IST)
    assert (local.hour, local.minute) == (8, 0)
    assert local.strftime("%A") == "Monday"
    assert T0.tzinfo is timezone.utc and T0 == datetime(2026, 9, 14, 2, 30, tzinfo=timezone.utc)


def test_district_timezone_is_display_only():
    d = build_sundargarh().district
    assert d.timezone == "Asia/Kolkata"
    assert d.forecast_at.tzinfo is timezone.utc


@pytest.mark.parametrize("day", [1, 2, 8, 14, 30])
def test_bucket_helpers_are_half_open(day):
    d = build_sundargarh().district
    start, end = d.day_start(day), d.day_end(day)
    assert end - start == DAY
    assert d.bucket_of(start) == day
    assert d.bucket_of(end - timedelta(microseconds=1)) == day
    assert d.bucket_of(end) == day + 1                   # the boundary belongs to the NEXT bucket
    assert d.day_end(day) == d.day_start(day + 1)


def test_before_t0_is_bucket_zero():
    d = build_sundargarh().district
    assert d.bucket_of(T0 - timedelta(seconds=1)) == 0


def test_day_at_offset_is_from_bucket_start():
    assert day_at(1) == T0
    assert day_at(1, 2) == T0 + timedelta(hours=2)                       # 10:00 IST clinic slot
    assert day_at(1, 2).astimezone(IST).hour == 10
    assert day_at(14) == T0 + DAY * 13


def test_bhatpar_indent_lands_exactly_on_day_14_boundary():
    st = build_sundargarh()
    s = st.supplies["sup-bhatpar-indent-001"]
    assert s.expected_arrival_at == T0 + timedelta(days=13)              # "13 days out"
    assert st.district.bucket_of(s.expected_arrival_at) == 14            # …credited in bucket 14, not 13


def test_warehouse_arrival_vs_breach_at_uses_timestamps():
    from havengrid.service import HavenGridService
    from havengrid.store import InMemoryRepository
    svc = HavenGridService(InMemoryRepository(build_sundargarh))
    svc.propose("case-bhatpar-amox-001")
    w = next(c for c in svc.current_plan("case-bhatpar-amox-001").candidates if c.donor_id == "warehouse")
    assert w.dispatch_ready_at == T0 + timedelta(hours=24)
    assert w.expected_arrival_at == T0 + timedelta(hours=168) == svc.repo.state().district.day_start(8)
    assert w.recipient_breach_at == svc.repo.state().district.day_end(8)
    assert w.recipient_breach_at - w.expected_arrival_at == DAY         # exactly one bucket of margin


def test_coverage_breach_and_recovery_timestamps_are_bucket_ends():
    from havengrid.kernel.interventions import forecast_for
    from havengrid.store import InMemoryRepository
    repo = InMemoryRepository(build_sundargarh)
    a = forecast_for(repo, "bhatpar", "amoxicillin-susp-125")
    d = repo.state().district
    assert a.coverage_breach_at == d.day_end(a.coverage_breach_day)
    assert a.stockout_at == d.day_end(a.stockout_day)
    assert a.recovery_at == d.day_end(a.recovery_day)
    assert a.coverage_breach_at < a.stockout_at < a.recovery_at


def test_care_event_timestamps_fall_inside_their_intended_buckets():
    st = build_sundargarh()
    d = st.district
    for e in st.care_events.values():
        b = d.bucket_of(e.scheduled_at)
        assert 1 <= b <= 14
        assert e.scheduled_at - d.day_start(b) == timedelta(hours=2)
