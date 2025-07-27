from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class WpRevision:
    timestamp: int
    text: str
    minor: bool = False

    @staticmethod
    def from_xml(data: Dict[str, Any]) -> "WpRevision":
        # Case the xml data into objects we expect,
        # we need to be compatible with the `Wikipedia` functions used below
        if data["timestamp"]:
            data["timestamp"] = datetime.fromtimestamp(int(data["timestamp"]))
        data["minor"] = data.get("minor") == "true"
        return WpRevision(**data)


@dataclass
class WpEdit:
    edit_id: int
    title: str
    namespace: str
    comment: str
    user: str
    creator: str
    user_edit_count: int
    user_distinct_pages: int
    user_warns: int
    prev_user: Optional[str]
    user_reg_time: int
    page_made_time: int
    num_recent_edits: int
    num_recent_reversions: int
    is_vandalism: bool
    current: WpRevision
    previous: Optional[WpRevision]

    @staticmethod
    def from_xml(data: Dict[str, Any]) -> "WpEdit":
        # Case the xml data into objects we expect,
        # we need to be compatible with the `Wikipedia` functions used below
        if data["user_reg_time"]:
            data["user_reg_time"] = datetime.fromtimestamp(int(data["user_reg_time"]))
        if data["page_made_time"]:
            data["page_made_time"] = datetime.fromtimestamp(int(data["page_made_time"]))
        if not data.get("namespace", None):
            data["namespace"] = "main"
        return WpEdit(**data)
