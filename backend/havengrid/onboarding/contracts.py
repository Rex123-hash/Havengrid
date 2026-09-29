"""Candidate-only contract for a future District Intelligence Agent."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol
from urllib.parse import urlparse

from pydantic import Field

from ..domain.models import Frozen


class CandidateFactStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    STALE = "stale"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class AuthorityClass(str, Enum):
    TRUSTED_GOVERNMENT = "trusted_government"
    PUBLIC_INSTITUTION = "public_institution"
    SECONDARY = "secondary"
    UNKNOWN = "unknown"


class DiscoveredFact(Frozen):
    field_name: str
    candidate_value: str | None
    source_url: str
    source_title: str
    publisher: str
    retrieved_at: datetime
    document_date: datetime | None = None
    confidence: Decimal = Field(ge=0, le=1)
    authority_class: AuthorityClass
    district_match: bool | None = None
    freshness_status: str = "unknown"
    status: CandidateFactStatus = CandidateFactStatus.CANDIDATE
    note: str = ""



class DistrictIntelligenceAgentContract(Protocol):
    """Future agent output boundary. Implementations may discover, never commit."""
    def discover(self, district_id: str) -> tuple[DiscoveredFact, ...]: ...


def deterministic_validation(fact: DiscoveredFact) -> DiscoveredFact:
    """Auto-verify only an objective, conflict-free official structured fact."""
    host = urlparse(fact.source_url).hostname or ""
    trusted = host.endswith(".gov.in") or host.endswith(".gov") or host.endswith(".nic.in")
    if trusted and fact.authority_class is AuthorityClass.TRUSTED_GOVERNMENT and fact.district_match is True and fact.candidate_value is not None and fact.status is CandidateFactStatus.CANDIDATE:
        return fact.model_copy(update={"status": CandidateFactStatus.VERIFIED})
    return fact
