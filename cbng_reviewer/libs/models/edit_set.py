import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WpRevision:
    timestamp: datetime = None
    user: Optional[str] = None
    comment: Optional[str] = None
    text: Optional[str] = None
    is_minor: bool = False
    is_creation: bool = False
    revision_id: Optional[int] = None

    @property
    def has_complete_training_data(self) -> bool:
        return self.timestamp is not None and self.text is not None

    def __str__(self) -> str:
        return f"WpRevision<{self.revision_id}>"

    @staticmethod
    def from_xml(data: Dict[str, Any]) -> Optional["WpRevision"]:
        if not data.get("timestamp"):
            return None
        return WpRevision(
            timestamp=datetime.fromtimestamp(int(data["timestamp"])),
            is_minor=data.get("minor") == "true",
            text=data.get("text"),
        )


@dataclass(frozen=True)
class WpEdit:
    edit_id: int = None
    title: str = None
    namespace: str = None
    comment: str = None
    user: str = None
    creator: str = None
    user_edit_count: Optional[int] = None
    user_distinct_pages: Optional[int] = None
    user_warns: Optional[int] = None
    prev_user: Optional[str] = None
    user_reg_time: datetime = None
    page_made_time: datetime = None
    num_recent_edits: Optional[int] = None
    num_recent_reversions: Optional[int] = None
    is_vandalism: bool = None
    current: WpRevision = None
    previous: Optional[WpRevision] = None
    editdb_source: Optional[str] = None
    reviewers: Optional[int] = None
    reviewers_agreeing: Optional[int] = None

    def __str__(self) -> str:
        return f"WpEdit<{self.edit_id}>"

    @property
    def has_complete_training_data(self) -> bool:
        if not self.title:
            logger.info(f"Missing title from {self}")
            return False

        if not self.page_made_time or not self.creator:
            logger.info(f"Missing page creation metadata from {self}")
            return False

        if not self.current or not self.current.has_complete_training_data:
            logger.info(f"Missing current revision data from {self}")
            return False

        if self.previous and not self.previous.has_complete_training_data:
            logger.info(f"Missing previous revision data from {self}")
            return False

        if not self.user_reg_time or self.user_warns is None or self.user_edit_count is None:
            logger.info(f"Missing user metadata from {self}")
            return False

        if self.num_recent_reversions is None or self.num_recent_edits is None:
            logger.info(f"Missing page metadata from {self}")
            return False

        return True

    @staticmethod
    def from_xml(data: Dict[str, Any]) -> "WpEdit":
        def handle_optional_int(data: Dict[str, Any], key: str) -> Optional[int]:
            if key in data:
                return int(data[key])
            return None

        def handle_optional_str(data: Dict[str, Any], key: str) -> Optional[int]:
            if key in data and data[key] is not None and len(data[key].strip()) > 0:
                return data[key]
            return None

        return WpEdit(
            # Ensure we type things according to the model
            edit_id=handle_optional_int(data, "edit_id"),
            user_edit_count=handle_optional_int(data, "user_edit_count"),
            user_distinct_pages=handle_optional_int(data, "user_distinct_pages"),
            user_warns=handle_optional_int(data, "user_warns"),
            num_recent_edits=handle_optional_int(data, "num_recent_edits"),
            num_recent_reversions=handle_optional_int(data, "num_recent_reversions"),
            is_vandalism=data["is_vandalism"] == "true",
            user_reg_time=datetime.fromtimestamp(handle_optional_int(data, "user_reg_time")),
            page_made_time=datetime.fromtimestamp(handle_optional_int(data, "page_made_time")),
            namespace=data.get("namespace", "main"),
            # WpRevision instances
            current=WpRevision.from_xml(data["current"]),
            previous=WpRevision.from_xml(data["previous"]),
            # Review interface data
            reviewers=handle_optional_int(data, "reviewers"),
            reviewers_agreeing=handle_optional_int(data, "reviewers_agreeing"),
            # Left over strings
            **{
                k: handle_optional_str(data, k)
                for k, v in data.items()
                if k in {"title", "comment", "user", "creator", "prev_user", "editdb_source"}
            },
        )
