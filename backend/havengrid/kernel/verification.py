"""Verification outcomes are four-valued. UNKNOWN never advances anything.

    expected  = canonical ± quantity (computed from the canonical record at the
                moment of verification — never from a stale plan snapshot)
    observed  = physical count / batch read supplied by the verifier

    observed is None                      → UNKNOWN
    observed == expected                  → VERIFIED
    observed == pre-transfer canonical    → NOT_APPLIED   (proves the movement did not happen)
    anything else                         → MISMATCH
"""

from __future__ import annotations

from ..domain.enums import VerificationOutcome


def classify_quantity(*, observed: int | None, expected: int, before: int) -> VerificationOutcome:
    if observed is None:
        return VerificationOutcome.UNKNOWN
    if observed == expected:
        return VerificationOutcome.VERIFIED
    if observed == before:
        return VerificationOutcome.NOT_APPLIED
    return VerificationOutcome.MISMATCH


def classify_batch(*, observed_batch_ids: list[str] | None, observed_quantity: int | None, expected_batch_ids: list[str], expected_quantity: int) -> VerificationOutcome:
    if observed_batch_ids is None or observed_quantity is None:
        return VerificationOutcome.UNKNOWN
    if not observed_batch_ids and observed_quantity == 0:
        return VerificationOutcome.NOT_APPLIED
    if sorted(observed_batch_ids) == sorted(expected_batch_ids) and observed_quantity == expected_quantity:
        return VerificationOutcome.VERIFIED
    return VerificationOutcome.MISMATCH
