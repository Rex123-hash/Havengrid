"""The kernel consumes canonical records; it must not care where they came from."""

from datetime import timezone

import pytest

from havengrid.domain.enums import CareCategory, Origin, ProvenanceStatus, SourceType
from havengrid.domain.models import CareObligation, Provenance
from havengrid.ingest.assembler import assemble
from havengrid.ingest.contracts import DataSource, DataSourceUnavailable
from havengrid.ingest.synthetic_source import SyntheticSundargarhSource
from havengrid.ingest.unavailable_source import UnavailableSource
from havengrid.kernel.care_impact import compute_care_impact
from havengrid.kernel.interventions import forecast_for
from havengrid.store import InMemoryRepository
from havengrid.synthetic.sundargarh import T0, build_sundargarh, day_at

ITEM = "amoxicillin-susp-125"


def _dump(st):
    return {
        "inv": sorted(r.model_dump_json() for r in st.inventory.values()),
        "sup": sorted(r.model_dump_json() for r in st.supplies.values()),
        "ce": sorted(r.model_dump_json() for r in st.care_events.values()),
        "b": sorted(r.model_dump_json() for r in st.batches.values()),
        "r": sorted(r.model_dump_json() for r in st.routes.values()),
        "d": sorted(r.model_dump_json() for r in st.demand.values()),
        "f": sorted(r.model_dump_json() for r in st.facilities.values()),
    }


def test_synthetic_source_satisfies_the_contract():
    assert isinstance(SyntheticSundargarhSource(), DataSource)
    assert isinstance(UnavailableSource(None, "x"), DataSource)


def test_assembling_the_synthetic_source_round_trips_the_fixture():
    assembled = assemble(SyntheticSundargarhSource(), open_case=("case-bhatpar-amox-001", "bhatpar", ITEM))
    direct = build_sundargarh()
    assert _dump(assembled) == _dump(direct)
    assert list(assembled.cases) == ["case-bhatpar-amox-001"]


def test_unavailable_source_raises_rather_than_returning_empty():
    with pytest.raises(DataSourceUnavailable) as e:
        assemble(UnavailableSource("hmis://x", "offline"))
    assert e.value.family == "district" and "offline" in e.value.reason


def test_assembler_rejects_two_canonical_records_for_one_facility_item():
    src = SyntheticSundargarhSource()
    dup = next(iter(src._st.inventory.values())).model_copy(update={"id": "dup"})
    src._st.inventory["dup"] = dup
    with pytest.raises(DataSourceUnavailable):
        assemble(src)


def test_kernel_result_is_identical_whatever_the_source_path():
    a = forecast_for(InMemoryRepository(build_sundargarh), "bhatpar", ITEM)
    b = forecast_for(InMemoryRepository(lambda: assemble(SyntheticSundargarhSource())), "bhatpar", ITEM)
    assert a.coverage_breach_day == b.coverage_breach_day == 8
    assert [r.closing for r in a.projection] == [r.closing for r in b.projection]


def test_kernel_outputs_are_model_derived_not_synthetic():
    a = forecast_for(InMemoryRepository(build_sundargarh), "bhatpar", ITEM)
    assert a.provenance.origin is Origin.MODEL_DERIVED


# ── aggregated care obligations (the privacy-preserving shape) ────────────


def _obligation(day, attendance, units=1, cat=CareCategory.PAEDIATRIC):
    return CareObligation(
        id=f"ob-{day}-{cat.value}", facility_id="bhatpar", category=cat, session_at=day_at(day, 2), item_id=ITEM,
        expected_attendance=attendance, units_per_attendance=units, description="immunisation session",
        units_basis="synthetic assumption",
        provenance=Provenance(source_type=SourceType.CARE_SCHEDULE, status=ProvenanceStatus.REPORTED, observed_at=T0,
                              source_ref="test", origin=Origin.SYNTHETIC_TEST),
    )


def test_obligations_add_demand_and_count_by_attendance():
    def build():
        st = build_sundargarh()
        # remove the 23 per-encounter rows and replace with two aggregated sessions on the same days
        st.care_events = {k: v for k, v in st.care_events.items() if v.facility_id != "bhatpar"}
        st.care_obligations["ob-a"] = _obligation(9, 8)                          # 8 paediatric attendances, day 9
        st.care_obligations["ob-b"] = _obligation(3, 5, cat=CareCategory.MATERNAL)  # day 3, before any breach
        return st

    repo = InMemoryRepository(build)
    a = forecast_for(repo, "bhatpar", ITEM)
    rows = {r.day: r for r in a.projection}
    assert rows[9].demand == 12 + 8 and rows[3].demand == 12 + 5
    impact = compute_care_impact(repo.state().district, a, repo.care_events_for("bhatpar", ITEM), repo.care_obligations_for("bhatpar", ITEM))
    assert impact.scheduled_in_window == 13
    assert a.coverage_breach_day is not None and a.coverage_breach_day < 9
    assert impact.exposed_obligation_ids == ("ob-9-paediatric",) and impact.exposed_total == 8
    assert impact.exposed_by_category[CareCategory.PAEDIATRIC] == 8 and impact.exposed_by_category[CareCategory.MATERNAL] == 0
    assert impact.exposed_units == 8


def test_mixed_events_and_obligations_sum_together():
    def build():
        st = build_sundargarh()
        st.care_obligations["ob-x"] = _obligation(10, 4, units=2, cat=CareCategory.SCHEDULED)
        return st

    repo = InMemoryRepository(build)
    a = forecast_for(repo, "bhatpar", ITEM)
    impact = compute_care_impact(repo.state().district, a, repo.care_events_for("bhatpar", ITEM), repo.care_obligations_for("bhatpar", ITEM))
    assert impact.scheduled_in_window == 23 + 4
    assert impact.exposed_total >= 13 + 4
    assert impact.exposed_by_category[CareCategory.SCHEDULED] >= 2 + 4
