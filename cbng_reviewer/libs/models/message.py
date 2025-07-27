from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    body: str
    subject: Optional[str] = None
