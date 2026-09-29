# Phase 0.8 regression-suite audit

The historical command documented before the Phase 0.7 additions was:

```text
.venv/Scripts/python -m pytest
```

The repository's current equivalent (the bundled environment was unavailable,
so the system Python was used with `PYTHONPATH=backend`) is:

```text
$env:PYTHONPATH='backend'; python -m pytest backend/tests
```

The pre-Phase-0.8 result was **122 collected, 122 passed, 0 skipped, 0
deselected**. The final Phase-0.8 result is **135 collected, 135 passed, 0
skipped, 0 deselected**.

The pre-Phase-0.7 baseline was 114 tests. Phase 0.7 added exactly one test file,
`tests/test_phase07.py`, containing 8 tests. No prior test file was deleted or
renamed, and `pyproject.toml` still collects the complete `tests/` directory.

Currently discovered files:

```text
test_api.py
test_care_impact.py
test_domain.py
test_environment_guard.py
test_evidence.py
test_fixture.py
test_forecast.py
test_ingest_boundary.py
test_interventions.py
test_phase07.py
test_phase08.py
test_state_machine.py
test_sundargarh_e2e.py
test_time_semantics.py
test_verification.py
```

The README's old `114 tests` note was stale after the Phase 0.7 file was added;
the test suite itself had not silently disappeared. Phase 0.8 adds
`test_phase08.py` to this same collection.

No test was deleted, renamed, skipped, or deselected during Phase 0.8.
The Phase 0.8 file now contains 13 semantic-gate and rehearsal tests.
