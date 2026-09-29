"""Temporary authorization seam for explicit operational commands.

This is deliberately a capability contract, not authentication.  Firebase/Auth
is a later phase.  The important invariant now is that page reads never invoke
commands and an operational command must carry an explicit actor capability.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .domain.enums import CaseAction
from .domain.errors import CommandNotAuthorized


DEFAULT_CAPABILITY = "temporary-operator-capability"


class CommandAuthorizer(Protocol):
    capability: str

    def authorize(self, *, action: CaseAction, actor: str, capability: str | None) -> None: ...


@dataclass(frozen=True)
class TemporaryCommandAuthorizer:
    """A testable actor/capability seam used until Auth is integrated."""

    capability: str = os.getenv("HAVENGRID_TEMP_COMMAND_CAPABILITY", DEFAULT_CAPABILITY)

    def authorize(self, *, action: CaseAction, actor: str, capability: str | None) -> None:
        if not actor.strip() or capability != self.capability:
            raise CommandNotAuthorized(
                "explicit operational command requires the temporary actor capability",
                action=action.value, actor=actor, capability_required=self.capability,
            )
