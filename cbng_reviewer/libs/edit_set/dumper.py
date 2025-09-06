import logging
import xml.etree.ElementTree as ET  # nosec: B405
from typing import Optional

from django.conf import settings

from cbng_reviewer.models import Edit, TrainingData, CurrentRevision, PreviousRevision

logger = logging.getLogger(__name__)


class EditSetDumper:
    def generate_wp_edit(self, edit: Edit) -> Optional[str]:
        try:
            training_data = TrainingData.objects.get(edit=edit)
        except TrainingData.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no training data")
            return None

        try:
            current_revision = CurrentRevision.objects.get(edit=edit)
        except CurrentRevision.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no current revision")
            return None

        try:
            previous_revision = PreviousRevision.objects.get(edit=edit)
        except PreviousRevision.DoesNotExist:
            logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no previous revision")
            if not current_revision.is_creation:
                logger.debug(f"Skipping generation of WPEdit for {edit.id} due to no previous revision")
                return None
            previous_revision = None

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
        ET.SubElement(current, "minor").text = "true" if current_revision.is_minor else "false"
        ET.SubElement(current, "timestamp").text = str(current_revision.timestamp)
        ET.SubElement(current, "text").text = current_revision.text.decode("utf-8")

        previous = ET.SubElement(wp_edit, "previous")
        if previous_revision:
            ET.SubElement(previous, "minor").text = "true" if previous_revision.is_minor else "false"
            ET.SubElement(previous, "timestamp").text = str(previous_revision.timestamp)
            ET.SubElement(previous, "text").text = previous_revision.text.decode("utf-8")

        if edit.status != 2:
            ET.SubElement(wp_edit, "reviewStatus").text = edit.get_status_display()
        else:
            ET.SubElement(wp_edit, "isVandalism").text = "true" if edit.classification == 0 else "false"
        return ET.tostring(wp_edit, encoding="unicode")
