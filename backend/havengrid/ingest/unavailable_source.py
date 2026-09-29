"""A configured-but-unreachable source. Every family raises; nothing is invented."""

from __future__ import annotations

from typing import NoReturn

from ..domain.enums import Origin
from .contracts import DataSourceUnavailable, SourceDescriptor


class UnavailableSource:
    def __init__(self, uri: str | None, reason: str) -> None:
        self.uri = uri
        self.reason = reason

    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(id=self.uri or "none", origin=Origin.OFFICIAL_SYSTEM_EXPORT, description=f"unavailable: {self.reason}")

    def _raise(self, family: str) -> NoReturn:
        raise DataSourceUnavailable(family, self.reason)

    def district(self):
        self._raise("district")

    def items(self):
        self._raise("items")

    def facilities(self):
        self._raise("facilities")

    def links(self):
        self._raise("links")

    def routes(self):
        self._raise("routes")

    def inventory(self):
        self._raise("inventory")

    def batches(self):
        self._raise("batches")

    def demand_profiles(self):
        self._raise("demand_profiles")

    def supplies(self):
        self._raise("supplies")

    def care_events(self):
        self._raise("care_events")

    def care_obligations(self):
        self._raise("care_obligations")
