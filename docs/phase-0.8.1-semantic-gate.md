# Phase 0.8.1 semantic gate

## Obligation provenance

The AMB KPI and IFA policy are real public programme context. The 11–15
Lahunipada range is a controlled facility-session rehearsal assumption because
the public 84.4% KPI has no Lahunipada denominator. The contract exposes
`numeric_basis_origin=REHEARSAL_ASSUMPTION`, `public_programme_basis=AMB`,
and `facility_denominator_status=UNKNOWN`.

## Care lifecycle

For cases with aggregate obligations, reconciliation now produces
`COVERAGE_RESTORED`; only a subsequent `DELIVERED` care-delivery record moves
the case to `CARE_PROTECTED`. `UNKNOWN`, `DEFERRED`, and `NOT_DELIVERED` remain
at `COVERAGE_RESTORED`. Event-only synthetic fixtures retain an explicit
compatibility path because their care rows are already explicit evidence. A
case with no exposed care refs has no delivery gate.

## Temporal audit

The trusted runtime clock was checked in UTC. Raw AMB, KPI, and Google route
captures are dated 2026-09-11 and precede the runtime clock. The coordinate
retrieval timestamp is UNKNOWN: the originally recorded 2026-09-12T00:00:00Z
is retained as unverified metadata, but no capture proves a corrected UTC
instant. The previously proposed 21:30 replacement was not substantiated.
Raw AMB and route captures were not rewritten. `Provenance.retrieved_at` now rejects
timestamps more than five minutes ahead of the trusted clock.

## Baseline and transfer units

The 56-tablet baseline is the controlled 4-tablet/day rehearsal rate multiplied
by the 14-day planning window. It is labelled `REHEARSAL_ASSUMPTION`, not
observed dispensing history. The 47-tablet transfer is a calculation quantity;
the physical dispatch/issue unit remains `UNKNOWN` because official pack data
was not captured.
