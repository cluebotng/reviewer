from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WikipediaEdit:
    title: str
    namespace: str
    timestamp: datetime
    previous_revision: Optional["WikipediaRevision"] = None
    current_revision: Optional["WikipediaRevision"] = None


@dataclass
class WikipediaRevision:
    minor: bool
    timestamp: datetime
    user: str
    comment: str
    text: str


@dataclass
class WikipediaPage:
    creation_user: str
    creation_time: datetime


@dataclass
class CentralUser:
    id: int
    username: str
