# HAVEN GRID backend — deterministic rehearsal and API

The default development API serves the current Sundargarh / IFA Red **controlled
rehearsal**. It starts after Lahunipada's 30-tablet observation and initial
Bonai plan, with Bonai's contradictory 20-tablet evidence awaiting review.
`GET /api/districts/sundargarh/workspace` returns a typed, read-only snapshot.
The historical Amoxicillin fixture remains available by explicitly setting
`HAVENGRID_DATA_SOURCE=synthetic` in development or test. Neither controlled
source is admitted in staging, judge, production, or operational mode. State
is in memory and no operational system or user authentication is connected.

## Purpose

Phase 0 makes the Sundargarh demonstration a set of **facts, policies and
deterministic calculations** rather than frontend-scripted outcomes. The kernel
derives every number the story tells — the breach day, the exposed care events,
the chosen donor, the transfer quantity, the corrected inventory, the revised
donor, the protected-care count — from the fixture. The fixture contains none of
those numbers.

Governing rule: **agents will propose; the deterministic kernel disposes.** There
are no agents yet; the contracts are shaped so that later AI can interpret
evidence, propose candidates and explain decisions without ever becoming the
source of truth.

## Environment integrity (Phase 0.5)

| `HAVENGRID_ENV` | `HAVENGRID_DATA_SOURCE` | Result |
|---|---|---|
| `development` / `test` (default) | `rehearsal` (default) | serves the current IFA Red checkpoint, labelled controlled rehearsal |
| `development` / `test` | `synthetic` (explicit) | serves the historical Amoxicillin regression fixture |
| `staging` / `judge` / `production` | `rehearsal` / `synthetic` | **`EnvironmentIntegrityError` at startup — the process will not start** |
| `staging` / `judge` / `production` | `none` (default) | starts **DEGRADED**: `/health` → `degraded`, every `/api/*` → `503 data_source_unavailable` |
| any | `official` (+ `HAVENGRID_OFFICIAL_SOURCE=`) | DEGRADED until an official adapter exists (later phase) |

Nothing is ever substituted. `/health` and every bundle report `data_origin.origins`
and `synthetic` so the frontend can answer *where did this number come from?*

### Origin vocabulary

`source_type` says what kind of record it is; `origin` says where it actually came from.

| origin | meaning |
|---|---|
| `synthetic_test` | invented for tests / labelled demos |
| `official_public_data` | a published public dataset |
| `official_system_export` | export from an operational system (HMIS, e-aushadhi…) |
| `user_supplied_evidence` | a human submitted it (photo, count, confirmation) |
| `live_external_api` | fetched from a live third-party service |
| `model_derived` | computed by the kernel from other records (all forecasts, plans) |
| `simulated_counterfactual` | a what-if the system constructed (candidate transfer simulations) |

Records created from human actions (confirmed evidence, verified counts, dispatches)
are stamped with the deployment's `actor_origin`: `synthetic_test` on the synthetic
source, `user_supplied_evidence` otherwise.

### Real-data adapter boundary

`havengrid/ingest/contracts.py` defines `DataSource` — the Protocols an official
source must implement (facilities, inventory, consumption, supply, care activity,
batches, routes) and, in its docstring, **the exact fields each family requires**.
`havengrid/ingest/assembler.py` builds the kernel's `ScenarioState` from a
configured source; the kernel never knows which. `SyntheticSundargarhSource`
remains the historical test source. Captured AMB and facility records are parsed
under `official/`; a Google Routes adapter and response capture exist under
`ingest/` and `data/raw/`. No official operational source is bootstrapped yet.

### Care activity without patient data

Two shapes feed the Care Blast Radius: `CareEvent` (one PHI-free encounter, opaque
id) and **`CareObligation`** (an aggregated session: `expected_attendance` ×
`units_per_attendance`, with a cited `units_basis`). Official sources are expected
to supply the aggregated shape.

## Run

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m uvicorn havengrid.api.app:app --port 8000
```

Interactive docs: <http://127.0.0.1:8000/docs>. Python 3.12+.

## Test

```bash
.venv/Scripts/python -m pytest
.venv/Scripts/python -m pytest tests/test_sundargarh_e2e.py -v
```

## Architecture

```
havengrid/
  domain/     enums.py, models.py, errors.py     — vocabularies, typed models, provenance
  kernel/     forecast.py                         — coverage forecast (pure)
              care_impact.py                      — Care Blast Radius (pure)
              interventions.py                    — sizing, feasibility, FEFO, ranking (pure)
              verification.py                     — four-valued verification (pure)
              state_machine.py                    — legal transitions
  synthetic/  sundargarh.py                       — SYNTHETIC TEST DATA: facts + policies only
  ingest/     contracts.py, assembler.py, …        — real-data adapter boundary (no fetching yet)
  settings.py, bootstrap.py                       — environment integrity guard, degraded mode
  store.py                                        — in-memory repository (the persistence seam)
  service.py                                      — commands, lineage, audit, synthetic clock
  api/        schemas.py, mappers.py, app.py      — typed FastAPI surface
```

The repository is in-memory. `reset` rebuilds it from the pure fixture
function, so replay is exact. `InMemoryRepository` is the boundary a database
implementation would fill later; no SQLAlchemy is used because nothing in
Phase 0 needs to survive a process restart.

## Domain concepts

| Concept | Meaning |
|---|---|
| **Provenance** | Every record: `source_type` (semantic kind), `status` (observed / reported / inferred / predicted / proposed / verified), `observed_at` (UTC), `source_ref`, `confidence`, **`origin`** (see *Origin vocabulary*). |
| **InventoryRecord** | One claim about stock. Exactly one is `canonical` per facility+item. Corrections create a new record with `supersedes_id`; the old one keeps its data and gains `superseded_by_id`. Nothing is overwritten. |
| **DemandProfile** | Baseline walk-in dispensing per day. Excludes scheduled care. |
| **CareEvent** | One appointment: facility, category, `scheduled_at`, item, `units_required` in generic dispensing units. |
| **IncomingSupply** | Quantity + `expected_arrival_at` + state. Credited to the bucket containing its arrival. |
| **CoverPolicy** | `min_cover_days = 3`, `planning_window_days = 14`, `horizon_days = 30`, dispatch lead hours per tier. |
| **Coverage breach** | First day-end at which closing inventory < the next 3 days of demand. |
| **Stockout** | First day-end at which closing inventory < 0. Distinct from coverage breach. |
| **Exposed care event** | Scheduled inside the uncovered interval `[coverage_breach_at, recovery_at)`. |
| **Transferable** | `min over the donor's protection window of (closing − cover)`. Derived, never seeded. |
| **Donor protection window** | `min(day of donor's next scheduled supply, planning window)`. |

## Equations implemented

```
demand(d)   = baseline(d) + Σ units_required(e)        e scheduled in bucket d
closing(d)  = closing(d−1) + credit(d) − demand(d)      closing(0) = canonical inventory
cover(d)    = demand(d+1) + demand(d+2) + demand(d+3)
covered(d)  = closing(d) ≥ cover(d)                     evaluated at bucket end, governs bucket d+1

coverage_breach_day = min { d : ¬covered(d) }           coverage_breach_at = day_end(b)
stockout_day        = min { d : closing(d) < 0 }
recovery_day        = min { d > b : covered(d) }        recovery_at = day_end(r)

exposed(e)   ⇔ coverage_breach_at ≤ e.scheduled_at < recovery_at
unserved(e)  ⇔ exposed(e) ∧ bucket(e) ≥ stockout_day

hold_through = bucket(recipient's next scheduled supply) − 1
q            = ceil_pack( max_{d ∈ [arrival_day, hold_through]} (cover(d) − closing(d)) )
transferable = min_{d ≤ W} (closing_donor(d) − cover_donor(d))
feasible     ⇔ route ∧ donor known ∧ donor not at risk in W ∧ q ≤ transferable
               ∧ arrival_at < coverage_breach_at ∧ recipient covered through hold_through
rank         = (¬expiry_relief, transit_hours, −post_transfer_margin)      lexicographic
```

As-of anchoring: a forecast starts from the canonical record's `observed_at`;
buckets already settled before it are skipped and supplies that arrived at or
before it are not credited again. This is what keeps a post-verification
re-forecast from double-counting the transfer.

## Scenario lifecycle

```
FORECASTED ─propose─▶ INTERVENTION_PROPOSED ─submit_evidence─▶ AWAITING_EVIDENCE_CONFIRMATION
  ─confirm_evidence─▶ EVIDENCE_CONFIRMED ─(system)─▶ PLAN_INVALIDATED ─(system)─▶ PLAN_RECALCULATED
  ─approve─▶ APPROVED ─dispatch─▶ DISPATCHED ─verify_source─▶ SOURCE_VERIFIED
  ─verify_destination─▶ DESTINATION_VERIFIED ─verify_batch─▶ BATCH_MATCHED
  ─reconcile─▶ COVERAGE_RESTORED ─care_delivery─▶ CARE_PROTECTED ─close─▶ CLOSED
```

* Illegal transitions return **409**. System actions cannot be issued externally.
* Verification is four-valued: `verified · not_applied · mismatch · unknown`.
  Only `verified` advances. **`unknown` is neither success nor failure.**
* `reconcile` computes: verified counts become canonical (with lineage), the
  transfer is marked received, the recipient is re-forecast, and the originally
  exposed refs are re-checked. Aggregate care obligations stop at
  `COVERAGE_RESTORED` until their delivery records are `delivered`; event-only
  fixtures use the explicit compatibility path to `CARE_PROTECTED`. There is
  no command that asserts it.
* `CLOSED` requires `CARE_PROTECTED`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness; declares `synthetic: true` |
| GET | `/api/demo/scenario` | one bundle: network, forecasts, care impacts, case, plans, evidence, lineage, verifications |
| POST | `/api/demo/reset` | rebuild from fixture; deterministic |
| GET | `/api/districts/{id}/network` | facilities, links, forecasts, care impacts |
| GET | `/api/districts/{id}/forecast?horizon_days=` | forecasts trimmed to a horizon |
| GET | `/api/facilities/{id}` | detail, inventory lineage, forecast, care events (each flagged exposed/unserved) |
| GET | `/api/facilities/{id}/care-impact` | Care Blast Radius |
| GET | `/api/cases/{id}` | case + legal actions |
| GET | `/api/cases/{id}/interventions` | every plan, oldest first, with candidates, checks, reason codes, allocations |
| GET | `/api/cases/{id}/audit` | audit trail |
| POST | `/api/cases/{id}/evidence` | `{facility_id, observed_quantity, confidence, captured_via?}` → awaiting confirmation |
| POST | `/api/cases/{id}/evidence/{eid}/confirm` | `{actor}` — commits corrected canonical, invalidates/replans |
| POST | `/api/cases/{id}/evidence/{eid}/reject` | `{actor, note}` |
| POST | `/api/cases/{id}/advance` | `{action, actor?, observed_quantity?, observed_batch_ids?, command_id?}` |

`command_id` makes any command idempotent.

## The Sundargarh fixture (facts only)

T0 = 2026-09-14 02:30 UTC (08:00 IST). Item: amoxicillin oral suspension, cartons of 10.

| Facility | Inventory | Baseline/day | Care events (window) | Next supply | Batches | Route → Bhatpar |
|---|---|---|---|---|---|---|
| Bhatpar PHC | 143 (count 3 d ago) | 12 | 23 | 200 on day 14 | — | recipient |
| CHC D · Kuchinda | 286 (count **9 d ago**) | 8 | 14 | 250 on day 21 | AMX-2401-K 90 exp day 21; AMX-2402-M 196 | 42 km · 1.5 h |
| CHC B · Hemgir | 340 | 7 | 6 | 300 on day 18 | AMX-2403-B 200; AMX-2404-C 140 | 68 km · 2.6 h |
| Kansbahal PHC | 150 | 14 | 17 | 200 on day 10 | — | 31 km · 1.1 h |
| Lahunipada PHC | 60 | 2 | 6 | 100 on day 20 | — | 27 km · 1.0 h |
| District Warehouse | 1 440 | 20 | 0 | — | AMX-2405-W | 96 km · 144 h (+24 h lead) |
| Kutra PHC | **none** | 6 | 3 | — | — | — |

## Derived values (from the kernel, asserted by tests)

Bhatpar: demand 191, gap 48, **coverage breach day 8**, stockout day 11, recovery day 14 ·
23 scheduled / **13 exposed** (7 paediatric · 4 maternal · 2 scheduled) / 6 unserved ·
transfer **80** (72 rounded to carton) · **CHC D chosen** (expiry relief) · CHC B rank 2 ·
warehouse rank 3 (arrives 24 h before breach) · Kansbahal `DONOR_ALREADY_AT_RISK` ·
Lahunipada `INSUFFICIENT_TRANSFERABLE_STOCK` · after confirming 126: CHC D breaches day 12,
plan-001 `INVALIDATED_BY_CONFIRMED_EVIDENCE`, **CHC B chosen** · after reconciliation:
Bhatpar 223, no breach in 30 days, **13 protected**.

## Synthetic-only assumptions (test fixture)

* one dispensing unit = one bottle; one encounter consumes one unit (no clinical basis claimed)
* flat baseline dispensing rates; 30-minute synthetic clock; a single item and case
* route table and dispatch lead hours are invented district policy

## Deterministic vs illustrative

**Deterministic (backend truth):** all of the above, evidence lineage, verification
outcomes, reconciliation, audit, reset.

**Illustrative / future work:** the handwritten-register visual in the frontend (the
backend only knows the observed quantity and confidence — there is no OCR); actors
are free-text strings (no auth); the synthetic clock advances 30 min per command;
a single item and a single case; no persistence across restarts; no AI.

## Frontend adapter

`VITE_SCENARIO_SOURCE=backend` makes the landing page replay the story on this
backend (reset → propose → evidence → confirm → approve → dispatch → verify ×3 →
reconcile → close) and render the derived state from three snapshots. Missing
backend-authoritative fields throw a `ScenarioContractError`. The default remains
the local seed; see the repository root `.env.example`.
