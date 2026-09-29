from havengrid.domain.enums import CareCategory, ForecastStatus


def test_bhatpar_care_blast_radius(svc, item_id):
    c = svc.care_impact("bhatpar", item_id)
    assert c.scheduled_in_window == 23
    assert c.exposed_total == 13
    assert c.exposed_by_category == {CareCategory.PAEDIATRIC: 7, CareCategory.MATERNAL: 4, CareCategory.SCHEDULED: 2}
    assert c.exposed_units == 13
    assert c.unserved_total == 6


def test_exposed_events_are_concrete_rows_in_uncovered_interval(svc, item_id, t0):
    from datetime import timedelta
    c = svc.care_impact("bhatpar", item_id)
    a = svc.forecast("bhatpar", item_id)
    rows = {e.id: e for e in svc.repo.care_events_for("bhatpar", item_id)}
    assert len(c.exposed_event_ids) == len(set(c.exposed_event_ids)) == 13
    for eid in c.exposed_event_ids:
        assert a.coverage_breach_at <= rows[eid].scheduled_at < a.recovery_at
    # events before the breach are served, not exposed
    served = [e for e in rows.values() if e.scheduled_at < a.coverage_breach_at]
    assert len(served) == 10 and not any(e.id in c.exposed_event_ids for e in served)


def test_unserved_subset_is_after_stockout(svc, item_id):
    c = svc.care_impact("bhatpar", item_id)
    a = svc.forecast("bhatpar", item_id)
    d = svc.repo.state().district
    rows = {e.id: e for e in svc.repo.care_events_for("bhatpar", item_id)}
    assert set(c.unserved_event_ids) <= set(c.exposed_event_ids)
    assert all(d.bucket_of(rows[i].scheduled_at) >= a.stockout_day for i in c.unserved_event_ids)


def test_no_breach_means_nothing_exposed(svc, item_id):
    c = svc.care_impact("remed", item_id)
    assert c.status is ForecastStatus.FORECAST and c.exposed_total == 0 and c.scheduled_in_window == 9


def test_unknown_forecast_has_unavailable_impact_not_zero(svc, item_id):
    c = svc.care_impact("kutra", item_id)
    assert c.status is ForecastStatus.UNAVAILABLE
    assert c.exposed_total is None and c.unserved_total is None
    assert c.exposed_by_category is None and c.coverage_breach_day is None
