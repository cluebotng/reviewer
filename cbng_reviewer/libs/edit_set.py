import logging
import tempfile
import xml.etree.ElementTree as ET  # nosec: B405
from pathlib import PosixPath
from typing import Optional

import requests
from django.conf import settings

from cbng_reviewer.libs.models.edit_set import WpEdit, WpRevision
from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import EditGroup, Edit, TrainingData, Revision

logger = logging.getLogger(__name__)


class EditSetDumper:
    def generate_wp_edit(self, edit: Edit) -> Optional[str]:
        try:
            training_data = TrainingData.objects.get(edit=edit)
        except TrainingData.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no training data")
            return None

        try:
            current_revision = Revision.objects.get(edit=edit, type=0)
        except Revision.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no current revision")
            return None

        try:
            previous_revision = Revision.objects.get(edit=edit, type=1)
        except Revision.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no previous revision")
            return None

        wp_edit = ET.Element("WPEdit")

        ET.SubElement(wp_edit, "EditType").text = "change"
        ET.SubElement(wp_edit, "EditID").text = str(edit.id)
        ET.SubElement(wp_edit, "comment").text = training_data.comment
        ET.SubElement(wp_edit, "user").text = training_data.user
        ET.SubElement(wp_edit, "user_edit_count").text = str(training_data.user_edit_count)
        ET.SubElement(wp_edit, "user_distinct_pages").text = str(training_data.user_distinct_pages)
        ET.SubElement(wp_edit, "user_warns").text = str(training_data.user_warns)
        ET.SubElement(wp_edit, "prev_user").text = training_data.prev_user
        ET.SubElement(wp_edit, "user_reg_time").text = str(training_data.user_reg_time)

        common = ET.SubElement(wp_edit, "common")
        ET.SubElement(common, "page_made_time").text = str(training_data.page_created_time)
        ET.SubElement(common, "title").text = training_data.page_title
        ET.SubElement(common, "namespace").text = settings.WIKIPEDIA_NAMESPACE_ID_TO_NAME[training_data.page_namespace]
        ET.SubElement(common, "creator").text = training_data.page_creator
        ET.SubElement(common, "num_recent_edits").text = str(training_data.page_num_recent_edits)
        ET.SubElement(common, "num_recent_reversions").text = str(training_data.page_num_recent_reverts)

        current = ET.SubElement(wp_edit, "current")
        ET.SubElement(current, "minor").text = "true" if current_revision.minor else "false"
        ET.SubElement(current, "timestamp").text = str(current_revision.timestamp)
        ET.SubElement(current, "text").text = current_revision.text.decode("utf-8")

        previous = ET.SubElement(wp_edit, "previous")
        ET.SubElement(previous, "minor").text = "true" if previous_revision.minor else "false"
        ET.SubElement(previous, "timestamp").text = str(previous_revision.timestamp)
        ET.SubElement(previous, "text").text = previous_revision.text.decode("utf-8")

        ET.SubElement(wp_edit, "isVandalism").text = "true" if edit.classification == 0 else "false"
        return ET.tostring(wp_edit, encoding="unicode")


class EditSetParser:
    def __init__(self):
        self._wikipedia = Wikipedia()

    def _flesh_out_edit(self, wp_edit: WpEdit) -> Optional[WpEdit]:
        if not wp_edit.page_made_time or not wp_edit.creator:
            if page_metadata := self._wikipedia.get_page_creation_metadata(wp_edit.title, wp_edit.namespace):
                wp_edit.page_made_time = page_metadata.creation_time
                wp_edit.creator = page_metadata.creation_user
            else:
                logger.warning(f"Failed to flesh out creation for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.current.text or not wp_edit.current.timestamp:
            current_revision, previous_revision = self._wikipedia.get_page_revisions(wp_edit.title, wp_edit.edit_id)
            if current_revision:
                wp_edit.current.timestamp = current_revision.timestamp
                wp_edit.current.text = current_revision.text
                wp_edit.current.minor = current_revision.minor

                if previous_revision:
                    wp_edit.previous.timestamp = previous_revision.timestamp
                    wp_edit.previous.text = previous_revision.text
                    wp_edit.previous.minor = previous_revision.minor

                    wp_edit.prev_user = previous_revision.user
                else:
                    wp_edit.previous = None
            else:
                logger.warning(f"Failed to flesh out revision for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.user_reg_time:
            if user_reg_time := self._wikipedia.get_user_registration_time(wp_edit.user):
                wp_edit.user_reg_time = user_reg_time
            else:
                logger.warning(f"Failed to flesh out user registration time for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.user_warns:
            if user_warns := self._wikipedia.get_user_warning_count(wp_edit.user, wp_edit.current.timestamp):
                wp_edit.user_warns = user_warns
            else:
                logger.warning(f"Failed to flesh out user warns count for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.user_edit_count:
            if user_edits := self._wikipedia.get_user_edit_count(wp_edit.user, wp_edit.current.timestamp):
                wp_edit.user_edit_count = user_edits
            else:
                logger.warning(f"Failed to flesh out user warns count for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.num_recent_reversions:
            if revert_count := self._wikipedia.get_page_recent_revert_count(
                wp_edit.user, wp_edit.namespace, wp_edit.current.timestamp
            ):
                wp_edit.num_recent_reversions = revert_count
            else:
                logger.warning(f"Failed to flesh out page revert count for edit {wp_edit.edit_id}")
                return None

        if not wp_edit.num_recent_edits:
            if edit_count := self._wikipedia.get_page_recent_edit_count(
                wp_edit.user, wp_edit.namespace, wp_edit.current.timestamp
            ):
                wp_edit.num_recent_edits = edit_count
            else:
                logger.warning(f"Failed to flesh out page edit count for edit {wp_edit.edit_id}")
                return None

        return wp_edit

    def download_and_import_to_group(self, target_group: EditGroup, path: str, partial_run: bool):
        with tempfile.NamedTemporaryFile() as file:
            logger.info(f"Downloading editset to {file.name}")
            r = requests.get(
                f"https://cluebotng-editsets.toolforge.org/{path}",
                timeout=10,
                headers={
                    "User-Agent": "ClueBot NG Reviewer - Edit Set Fetch",
                },
                stream=True,
            )
            if r.status_code != 200:
                logger.error(f"Failed to download {path}, skipping processing")
                return

            for chunk in r.iter_content(chunk_size=512):
                file.write(chunk)

            # Parse
            return self.import_to_group(target_group, PosixPath(file.name), partial_run)

    def _import_training_data(self, edit: Edit, target_group: EditGroup, wp_edit: WpEdit):
        TrainingData.objects.filter(edit=edit).delete()
        TrainingData.objects.create(
            edit=edit,
            timestamp=wp_edit.current.timestamp.timestamp(),
            comment=wp_edit.comment,
            user=wp_edit.user,
            user_edit_count=wp_edit.user_edit_count,
            user_distinct_pages=wp_edit.user_distinct_pages,
            user_warns=wp_edit.user_warns,
            user_reg_time=wp_edit.user_reg_time.timestamp(),
            prev_user=wp_edit.prev_user,
            page_title=wp_edit.title,
            page_namespace=settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[wp_edit.namespace.lower()],
            page_created_time=wp_edit.page_made_time.timestamp(),
            page_creator=wp_edit.creator,
            page_num_recent_edits=wp_edit.num_recent_edits,
            page_num_recent_reverts=wp_edit.num_recent_reversions,
        )

        if wp_edit.current or wp_edit.previous:
            Revision.objects.filter(edit=edit).delete()
            if wp_edit.current:
                Revision.objects.create(
                    edit=edit,
                    type=0,
                    minor=wp_edit.current.minor,
                    timestamp=wp_edit.current.timestamp.timestamp(),
                    text=wp_edit.current.text.encode("utf-8"),
                )

            if wp_edit.previous:
                Revision.objects.create(
                    edit=edit,
                    type=1,
                    minor=wp_edit.previous.minor,
                    timestamp=wp_edit.previous.timestamp.timestamp(),
                    text=wp_edit.previous.text.encode("utf-8"),
                )

        if not edit.groups.filter(pk=target_group.pk).exists():
            logger.info(f"Adding {edit.id} to {target_group.name}")
            edit.groups.add(target_group)

    def import_to_group(self, target_group: EditGroup, path: PosixPath, partial_run: bool):
        mapped_fields = {
            "EditID": "edit_id",
            "isVandalism": "is_vandalism",
        }
        accepted_fields = [
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

        revision_fields = ["minor", "timestamp", "text"]

        current_edit, current_revision, previous_revision = None, None, None
        for context, elem in ET.iterparse(path, events=("start", "end")):  # nosec: B314
            if elem.tag == "WPEdit":
                # Start a new blank edit that we will fill out
                if context == "start":
                    current_edit = {}

                # Handle the import logic
                if context == "end" and current_edit:
                    wp_edit = WpEdit.from_xml(current_edit)
                    try:
                        edit = Edit.objects.get(id=wp_edit.edit_id)
                    except Edit.DoesNotExist:
                        edit = None

                    if partial_run and edit and edit.has_training_data:
                        logger.info(f"Skipping WpEdit entry for existing edit: {wp_edit.edit_id}")
                        continue

                    if self._wikipedia.has_revision_been_deleted(wp_edit.edit_id):
                        logger.info(f"Skipping WpEdit due to deletion: {wp_edit.edit_id}")
                        if edit and not edit.deleted:
                            logger.info(f"Marking edit as deleted: {edit.id}")
                            edit.deleted = True
                            edit.save()
                        return None

                    logger.info(f"Handling WpEdit entry: {wp_edit.edit_id}")
                    if wp_edit := self._flesh_out_edit(wp_edit):
                        if not edit:
                            logger.info(f"Created edit for {wp_edit.edit_id}")
                            edit = Edit.objects.create(
                                id=wp_edit.edit_id, classification=0 if wp_edit.is_vandalism else 1, status=2
                            )

                        self._import_training_data(edit, target_group, wp_edit)
                    current_edit = None

            if current_edit is None:
                continue

            if current_revision is not None and context == "end" and elem.tag in revision_fields:
                current_revision[elem.tag] = elem.text
                continue

            if elem.tag == "current":
                if context == "start":
                    current_revision = {}

                elif context == "end" and current_revision is not None:
                    current_edit["current"] = WpRevision.from_xml(current_revision)
                    current_revision = None

                continue

            if previous_revision is not None and context == "end" and elem.tag in revision_fields:
                previous_revision[elem.tag] = elem.text
                continue

            if elem.tag == "previous":
                if context == "start":
                    previous_revision = {}

                elif context == "end" and previous_revision is not None:
                    current_edit["previous"] = WpRevision.from_xml(previous_revision)
                    previous_revision = None

                continue

            if current_edit is not None and context == "end":
                if elem.tag in accepted_fields:
                    current_edit[elem.tag] = elem.text
                elif mapped_field := mapped_fields.get(elem.tag):
                    current_edit[mapped_field] = elem.text

                match elem.tag:
                    case "EditID":
                        current_edit["edit_id"] = elem.text
                    case "comment":
                        current_edit["comment"] = elem.text
                    case "user":
                        current_edit["comment"] = elem.text
