import logging
import xml.etree.ElementTree as ET  # nosec: B405
from pathlib import PosixPath
from typing import Optional, Dict, Any, Tuple, Callable

from cbng_reviewer.libs.models.edit_set import WpEdit

logger = logging.getLogger(__name__)


class EditSetParser:
    def __init__(self):
        self._ignore_fields = {
            "WPEditSet",
        }
        self._mapped_fields = {
            "EditID": "edit_id",
            "isVandalism": "is_vandalism",
        }
        self._edit_fields = [
            "comment",
            "user",
            "user_edit_count",
            "user_distinct_pages",
            "user_warns",
            "prev_user",
            "user_reg_time",
            "page_made_time",
            "title",
            "namespace",
            "creator",
            "num_recent_edits",
            "num_recent_reversions",
        ]
        self._revision_fields = ["minor", "timestamp", "text"]
        self._review_interface_fields = ["reviewers", "reviewers_agreeing"]

    def _new_processing_context(self, in_edit: bool = False) -> Dict[str, Any]:
        return {
            "edit": {"current": {}, "previous": {}},
            "in_edit": in_edit,
            "in_current": False,
            "in_previous": False,
            "in_editdb": False,
            "in_reviewinterface": False,
        }

    def _process_element(
        self, ctx: Dict[str, Any], context: str, elem: ET.Element
    ) -> Tuple[Dict[str, Any], Optional[WpEdit]]:
        if elem.tag == "WPEdit":
            wp_edit = None
            # We have an exit context and are at </WPEdit>, load the data into the model
            if context == "end" and ctx["in_edit"]:
                wp_edit = WpEdit.from_xml(ctx["edit"])

            # Start a new context (at <WPEdit> or </WPEdit>)
            ctx = self._new_processing_context(True)

            # Return wp_edit (or None)
            return ctx, wp_edit

        # We are not in an edit context - ignore the fields
        if not ctx["in_edit"]:
            if elem.tag not in self._ignore_fields:
                logger.warning(f"Ignoring {elem.tag} ({elem.tag})")
            return ctx, None

        # Handle changing in / out of the <current> / <previous> blocks
        if elem.tag in {"current", "previous", "EditDB", "ReviewInterface"}:
            match context:
                case "start":
                    ctx[f"in_{elem.tag.lower()}"] = True
                case "end":
                    ctx[f"in_{elem.tag.lower()}"] = False
            return ctx, None

        # We are in the context of the current edit - touch the current data fields
        if ctx["in_current"]:
            if context == "end" and elem.tag in self._revision_fields:
                ctx["edit"]["current"][elem.tag] = elem.text
            return ctx, None

        # We are in the context of the current edit - touch the previous data fields
        if ctx["in_previous"]:
            if context == "end" and elem.tag in self._revision_fields:
                ctx["edit"]["previous"][elem.tag] = elem.text
            return ctx, None

        # We are in the context of the editdb - grab the source
        if ctx["in_editdb"]:
            if context == "start" and elem.tag == "source":
                ctx["edit"]["editdb_source"] = elem.text
            return ctx, None

        # We are in the context of the review interface - grab the stats
        if ctx["in_reviewinterface"]:
            if context == "end" and elem.tag in self._review_interface_fields:
                ctx["edit"][elem.tag] = elem.text
            return ctx, None

        # We are in the context of the edit generally - touch the edit data fields
        if context == "end":
            if elem.tag in self._edit_fields:
                ctx["edit"][elem.tag] = elem.text
            elif mapped_field := self._mapped_fields.get(elem.tag):
                ctx["edit"][mapped_field] = elem.text

        return ctx, None

    def read_file(self, path: PosixPath, callback_func: Optional[Callable] = None) -> bool:
        if not path.exists():
            logger.error(f"Specified file does not exist: {path.as_posix()}")
            return False

        try:
            processing_context = self._new_processing_context()
            for context, elem in ET.iterparse(path, events=("start", "end")):  # nosec: B314
                processing_context, wp_edit = self._process_element(processing_context, context, elem)
                if wp_edit and callback_func:
                    callback_func(wp_edit=wp_edit)
        except ET.ParseError as e:
            logger.error(f"Could not parse {path.as_posix()}: {e}")
            return False

        return True
