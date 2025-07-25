import dataclasses
from datetime import datetime
from typing import Optional


@dataclasses.dataclass
class WikipediaEdit:
    title: str
    namespace: str
    timestamp: datetime
    previous_revision: Optional["WikipediaRevision"] = None
    current_revision: Optional["WikipediaRevision"] = None


@dataclasses.dataclass
class WikipediaRevision:
    minor: bool
    timestamp: datetime
    user: str
    comment: str
    text: str


@dataclasses.dataclass
class WikipediaPage:
    creation_user: str
    creation_time: datetime
