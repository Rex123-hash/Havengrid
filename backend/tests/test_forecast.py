from datetime import timedelta

from havengrid.domain.enums import ForecastStatus
from havengrid.kernel.forecast import quantity_to_hold, round_up_to_pack, transferable_through_window
from havengrid.kernel.interventions import forecast_for


def test_bhatpar_coverage_breach_day_8_and_stockout_day_11(svc, item_id, t0):
    a = svc.forecast("bhatpar", item_id)
    assert a.status is ForecastStatus.FORECAST
    assert a.coverage_breach_day == 8
    assert a.coverage_breach_at == t0 + timedelta(days=8)
    assert a.stockout_day == 11
    assert a.stockout_at == t0 + timedelta(days=11)
    assert a.recovery_day == 14
    assert a.recovery_at == t0 + timedelta(days=14)


def test_bhatpar_projection_arithmetic(svc, item_id):
    a = svc.forecast("bhatpar", item_id)
    rows = {r.day: r for r in a.projection}
    assert sum(r.demand for r in a.projection if r.day <= 14) == 191
    assert rows[7].closing == 52 and rows[7].cover_required == 46 and rows[7].covered
    assert rows[8].closing == 37 and rows[8].cover_required == 47 and not rows[8].covered
    assert rows[10].closing == 6 and rows[11].closing == -10
    assert rows[14].credit == 200 and rows[14].closing == 152 and rows[14].covered


def test_coverage_uses_strict_less_than(svc, item_id):
    # closing == cover must count as covered
    a = svc.forecast("bhatpar", item_id)
    for r in a.projection:
        assert r.covered == (r.closing >= r.cover_required)


def test_unknown_inventory_is_unavailable_not_healthy(svc, item_id):
    a = svc.forecast("kutra", item_id)
    assert a.status is ForecastStatus.UNAVAILABLE
    assert a.coverage_breach_day is None
    assert "NOT 'healthy'" in a.drivers[0]


def test_network_breach_days(svc, item_id):
    days = {fid: a.coverage_breach_day for fid, a in svc.network_forecast(item_id).items()}
    assert days["bhatpar"] == 8
    assert days["kansbahal"] == 7
    assert days["nuagaon"] == 11
    assert days["chc-d"] is None       # day-21 indent covers it at 286
    assert days["chc-b"] is None and days["warehouse"] is None and days["remed"] is None


def test_as_of_anchoring_skips_settled_buckets_and_arrived_supplies(svc, item_id, t0):
    from havengrid.kernel.forecast import assess_coverage
    d = svc.repo.state().district
    later = t0 + timedelta(days=2, hours=3)  # inside bucket 3
    a = assess_coverage(d, facility_id="bhatpar", item_id=item_id, starting_inventory=100,
                        profile=svc.repo.demand_profile("bhatpar", item_id), events=svc.repo.care_events_for("bhatpar", item_id),
                        supplies=svc.repo.supplies_for("bhatpar", item_id), as_of=later)
    assert a.projection[0].day == 3 and a.projection[0].opening == 100


def test_quantity_to_hold_and_pack_rounding(svc, item_id):
    a = svc.forecast("bhatpar", item_id)
    assert quantity_to_hold(a, credited_on_day=1, hold_through_day=13) == 72
    assert round_up_to_pack(72, 10) == 80
    assert round_up_to_pack(80, 10) == 80
    assert round_up_to_pack(0, 10) == 0


def test_transferable_is_min_margin_over_window(svc, item_id):
    a = forecast_for(svc.repo, "chc-d", item_id)
    assert transferable_through_window(a, window_days=14) == min(r.closing - r.cover_required for r in a.projection[:14])
