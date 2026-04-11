from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Channel:
    name: str


@dataclass
class VhostConfig:
    name: str
    channels: Optional[List[str]] = None

    def get_channels(self) -> List[str]:
        """Return channels list, default to empty if not provided."""
        return self.channels or []


@dataclass
class Action:
    status: str
    resource: str
    name: str
    details: str = ""


@dataclass
class BootstrapSettings:
    api_url: str
    username: str
    password: str
