"""The fixture must contain facts and policies only — never derivable outcomes."""

import inspect

from havengrid.domain.enums import Origin
from havengrid.synthetic import sundargarh
from havengrid.synthetic.sundargarh import ITEM, build_sundargarh


def test_fixture_has_14_facilities_and_one_item():
    st = build_sundargarh()
    assert len(st.facilities) == 14
    assert set(st.items) == {ITEM}


def test_bhatpar_has_23_concrete_care_event_rows():
    st = build_sundargarh()
    rows = [e for e in st.care_events.values() if e.facility_id == "bhatpar"]
    assert len(rows) == 23
    by = {}
    for e in rows:
        by[e.category.value] = by.get(e.category.value, 0) + 1
    assert by == {"paediatric": 11, "maternal": 7, "scheduled": 5}
    assert all(e.units_required == 1 for e in rows)


def test_every_record_is_marked_synthetic():
    st = build_sundargarh()
    provs = [r.provenance for r in st.inventory.values()] + [r.provenance for r in st.supplies.values()] + \
            [r.provenance for r in st.care_events.values()] + [r.provenance for r in st.batches.values()] + \
            [r.provenance for r in st.routes.values()] + [r.provenance for r in st.demand.values()] + [st.district.policy.provenance]
    assert provs and all(p.origin is Origin.SYNTHETIC_TEST for p in provs)


def _code_only(module) -> str:
    """Source with the module docstring and comment lines removed."""
    src = inspect.getsource(module)
    if module.__doc__:
        src = src.replace(module.__doc__, "", 1)
    lines = [line for line in src.splitlines() if not line.strip().startswith("#")]
    return chr(10).join(lines)


def test_fixture_source_contains_no_derived_outcomes():
    src = _code_only(sundargarh)
    for banned in ("verdict", "breach_day", "breachDay", "exposed", "chosen", "resulting", "protected_count", "CandidateVerdict"):
        assert banned not in src, f"fixture must not seed derivable outcome '{banned}'"


def test_kutra_has_no_canonical_inventory():
    st = build_sundargarh()
    assert not any(r.facility_id == "kutra" for r in st.inventory.values())


def test_fixture_build_is_deterministic():
    a, b = build_sundargarh(), build_sundargarh()
    assert [r.model_dump() for r in a.inventory.values()] == [r.model_dump() for r in b.inventory.values()]
    assert [e.model_dump() for e in a.care_events.values()] == [e.model_dump() for e in b.care_events.values()]
