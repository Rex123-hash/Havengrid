"""Deployment environment and data-source policy.

    DEVELOPMENT / TEST     current rehearsal default; historical fixture explicit
    STAGING / JUDGE / PROD backend data source required; controlled fixtures forbidden

The guard is enforced at construction time (`validate`) so a misconfigured
process refuses to start rather than quietly serving invented facts as the
world it claims to observe. An official source that is configured but
unreachable does not crash the process: the app starts DEGRADED and every data
endpoint answers 503 until the source is available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from .domain.enums import Origin


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover
        return str(self.value)


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    JUDGE = "judge"
    PRODUCTION = "production"


class DataSourceKind(StrEnum):
    REHEARSAL = "rehearsal"      # current Sundargarh / IFA Red interactive checkpoint
    SYNTHETIC = "synthetic"      # historical Amoxicillin regression fixture, explicit opt-in
    OFFICIAL = "official"        # an implementation of havengrid.ingest.contracts.DataSource
    NONE = "none"                # nothing configured → degraded


class HavenGridMode(StrEnum):
    REHEARSAL = "rehearsal"
    OPERATIONAL = "operational"


SYNTHETIC_PERMITTED = frozenset({Environment.DEVELOPMENT, Environment.TEST})


class EnvironmentIntegrityError(RuntimeError):
    """Raised when a configuration would let synthetic data pose as operational truth."""


@dataclass(frozen=True)
class Settings:
    env: Environment
    data_source: DataSourceKind
    official_source_uri: str | None = None
    mode: HavenGridMode = HavenGridMode.REHEARSAL

    @property
    def synthetic_permitted(self) -> bool:
        return self.env in SYNTHETIC_PERMITTED

    @property
    def actor_origin(self) -> Origin:
        """Origin stamped on records created from human actions in this deployment
        (confirmed evidence, verified counts, dispatches)."""
        return Origin.SYNTHETIC_TEST if self.data_source is DataSourceKind.SYNTHETIC else Origin.USER_SUPPLIED_EVIDENCE

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Settings":
        e = environ if environ is not None else os.environ
        env = Environment(e.get("HAVENGRID_ENV", Environment.DEVELOPMENT.value).lower())
        default_source = DataSourceKind.REHEARSAL if env in SYNTHETIC_PERMITTED else DataSourceKind.NONE
        source = DataSourceKind(e.get("HAVENGRID_DATA_SOURCE", default_source.value).lower())
        mode = HavenGridMode(e.get("HAVENGRID_MODE", HavenGridMode.REHEARSAL.value).lower())
        return cls(env=env, data_source=source, official_source_uri=e.get("HAVENGRID_OFFICIAL_SOURCE"), mode=mode)


def validate(settings: Settings) -> Settings:
    if settings.data_source in (DataSourceKind.SYNTHETIC, DataSourceKind.REHEARSAL) and not settings.synthetic_permitted:
        raise EnvironmentIntegrityError(
            f"HAVENGRID_ENV={settings.env.value} forbids rehearsal or synthetic data sources. "
            "Controlled data may test HAVEN GRID; it must not pretend to be operational truth."
        )
    if settings.mode is HavenGridMode.OPERATIONAL and settings.data_source in (DataSourceKind.SYNTHETIC, DataSourceKind.REHEARSAL):
        raise EnvironmentIntegrityError("HAVENGRID_MODE=operational requires an official or user-evidence source; controlled replay is rehearsal-only.")
    return settings
