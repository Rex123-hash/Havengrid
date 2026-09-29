"""Domain errors. Each maps to a specific HTTP status in the API layer."""

from __future__ import annotations


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, **detail: object) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFound(DomainError):
    code = "not_found"


class IllegalTransition(DomainError):
    code = "illegal_transition"


class InvariantViolation(DomainError):
    code = "invariant_violation"


class VerificationFailed(DomainError):
    """A verification step observed reality that does not match expectation.
    The case does NOT advance. This is the 'API success != workflow success' error."""

    code = "verification_failed"


class CommandNotAuthorized(DomainError):
    """Operational command was not presented through the explicit capability seam."""

    code = "command_not_authorized"
