# Phase 0.8 JudgeScenarioContract

The machine-readable contract is `havengrid.rehearsal.contracts.JudgeScenarioContract` and the deterministic builder is `havengrid.rehearsal.sundargarh.run_sundargarh_rehearsal()`.

The current captured run is:

| Field | Value | Evidence class |
|---|---:|---|
| District | Sundargarh, Odisha | official public context |
| Recipient | Community Health Centre Lahunipada, Lahunipada block | Odisha official referral directory; current verified |
| Commodity | IFA Red, 60 mg elemental iron + 500 µg folic acid | AMB policy |
| District stock context | FY 2025–26, data as on 2026-06-03; figures in lakhs | AMB public stock dashboard |
| Initial recipient inventory | 30 tablets | `REHEARSAL_FIELD_OBSERVATION`, confirmed by rehearsal pharmacist |
| Initial coverage breach | day 5 | deterministic kernel |
| Initial physical stockout | day 8 | deterministic kernel |
| Aggregate exposed obligation | 11–15; midpoint 13 for deterministic arithmetic | `PROGRAMME_ESTIMATED` with `numeric_basis_origin=REHEARSAL_ASSUMPTION`; AMB KPI and IFA policy provide public context only |
| Initial donor | SDH Bonai, 47 tablets | deterministic kernel using captured Google route |
| Corrected donor observation | 20 tablets | `REHEARSAL_FIELD_OBSERVATION`, confirmed by rehearsal pharmacist |
| Replacement donor | SDH Panposh, 47 tablets | deterministic kernel using captured Google route |
| Coverage recovery | `COVERAGE_RESTORED` at reconciliation; then one aggregate obligation verified as delivered and case reaches `CARE_PROTECTED` | deterministic reconciliation, followed by a separate care-delivery record |

The contract contains both `initial_donor_candidates` and the post-correction `donor_candidates`, route distance/duration/static duration, retrieval timestamp, provider, request hash, candidate rejection reasons, field-evidence correction, coverage restoration, care-delivery verification, lifecycle actions, provenance labels, exact fact classifications, derived-from references, and explicit unknown facts. The frontend migration must consume this object rather than recomputing values from raw rows.

`fact_classifications` uses exactly `REAL_PUBLIC`, `LIVE_EXTERNAL_API`,
`REHEARSAL_EVIDENCE`, `REHEARSAL_ASSUMPTION`, `MODEL_DERIVED`, and `UNKNOWN`.
Every `MODEL_DERIVED` path has a non-empty `derived_from` entry, and every
`REHEARSAL_ASSUMPTION` path has an `assumption_notes` entry.

Its `programme_obligation.allocation_method_comparison` records the two
defensible options considered: the controlled 11–15 facility-session range
(used, midpoint 13) and a district-percentage-preserving allocation (left
`UNKNOWN` because the public 84.4% KPI has no Lahunipada denominator).

The contract also marks the controlled baseline demand as
`REHEARSAL_ASSUMPTION`, and exposes `physical_dispatch_unit=UNKNOWN` so the
47-tablet calculation cannot be mistaken for a confirmed pack quantity.

The route cassette is `data/raw/live/google_routes/sundargarh-lahunipada-matrix.json`. It contains four `Compute Routes` responses captured on 2026-09-11 and is replayed only as labelled rehearsal input. A live adapter with no credential or an unavailable provider response yields `ROUTE_UNAVAILABLE` and no distance or duration.
