"""Turns Settings into a running service — or an honest DEGRADED state.

    rehearsal + permitted        → current IFA Red interactive checkpoint
    synthetic + permitted        → explicit historical regression fixture
    controlled + forbidden       → EnvironmentIntegrityError (refuse to start)
    official  + reachable        → service on that source        (later phase)
    official  + unreachable      → DEGRADED, reason recorded
    none                         → DEGRADED, "no data source configured"
"""

from __future__ import annotations

from dataclasses import dataclass

from .ingest.assembler import assemble
from .ingest.contracts import DataSource, DataSourceUnavailable
from .ingest.synthetic_source import SyntheticSundargarhSource
from .ingest.unavailable_source import UnavailableSource
from .service import HavenGridService
from .rehearsal.sundargarh import build_sundargarh_rehearsal_checkpoint
from .domain.enums import Origin
from .settings import DataSourceKind, Settings, validate
from .store import InMemoryRepository

HISTORICAL_FOCUS_CASE = ("case-bhatpar-amox-001", "bhatpar", "amoxicillin-susp-125")


@dataclass
class Bootstrapped:
    settings: Settings
    service: HavenGridService | None
    source_id: str
    source_origin: str
    degraded_reason: str | None

    @property
    def degraded(self) -> bool:
        return self.service is None


def resolve_source(settings: Settings) -> DataSource:
    if settings.data_source is DataSourceKind.SYNTHETIC:
        return SyntheticSundargarhSource()
    if settings.data_source is DataSourceKind.OFFICIAL:
        # The boundary exists; no official adapter is implemented in this build.
        return UnavailableSource(settings.official_source_uri, "no official data-source adapter is implemented in this build")
    return UnavailableSource(None, "no data source configured (HAVENGRID_DATA_SOURCE=none)")


def bootstrap(settings: Settings) -> Bootstrapped:
    validate(settings)
    if settings.data_source is DataSourceKind.REHEARSAL:
        repo = InMemoryRepository(build_sundargarh_rehearsal_checkpoint)
        return Bootstrapped(
            settings=settings,
            service=HavenGridService(repo, actor_origin=Origin.USER_SUPPLIED_EVIDENCE,
                                     mode=settings.mode),
            source_id="rehearsal/sundargarh-ifa-red",
            source_origin="controlled_rehearsal",
            degraded_reason=None,
        )
    source = resolve_source(settings)
    desc = source.descriptor()
    try:
        repo = InMemoryRepository(lambda: assemble(source, open_case=HISTORICAL_FOCUS_CASE))
    except DataSourceUnavailable as e:
        return Bootstrapped(settings=settings, service=None, source_id=desc.id, source_origin=desc.origin.value, degraded_reason=str(e))
    return Bootstrapped(
        settings=settings,
        service=HavenGridService(repo, actor_origin=settings.actor_origin, mode=settings.mode),
        source_id=desc.id,
        source_origin=desc.origin.value,
        degraded_reason=None,
    )
