import logging
from typing import Optional
from xml.etree import ElementTree as ET  # nosec: B405

from django.conf import settings

from cbng_reviewer.models import Edit, TrainingData, CurrentRevision, PreviousRevision, EditGroup, ScoreData

logger = logging.getLogger(__name__)


class EditSetDumper:
    def _extended_escape_cdata(self, text: Optional[str]) -> Optional[str]:
        text = ET._original_escape_cdata(text)
        # This matches the old behaviour, though is not an XML standard =\
        if '"' in text:
            text = text.replace('"', "&quot;")
        return text

    def _xml_to_string(self, wp_edit: ET.Element, indent_block: bool) -> str:
        # Indent all (child) elements
        ET.indent(wp_edit, space=" ")

        # Monkey patch
        ET._original_escape_cdata = ET._escape_cdata
        ET._escape_cdata = self._extended_escape_cdata

        output = ET.tostring(wp_edit, encoding="unicode", short_empty_elements=False)

        # Remove the monkey
        ET._escape_cdata = ET._original_escape_cdata
        delattr(ET, "_original_escape_cdata")

        if indent_block:
            lines = []
            for line in output.splitlines():
                if line.strip().startswith("<"):
                    line = f" {line}"
                lines.append(line)
            output = "\n".join(lines)

        return output

    def generate_wp_edit(
        self, edit: Edit, edit_group: Optional[EditGroup] = None, indent_block: bool = False
    ) -> Optional[str]:
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

        edit_db = ET.SubElement(wp_edit, "EditDB")
        ET.SubElement(edit_db, "isActive").text = "true"
        if edit_group:
            ET.SubElement(edit_db, "source").text = edit_group.name
        ET.SubElement(edit_db, "lastUpdated").text = edit.last_updated.strftime("%s")

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

        namespace = settings.WIKIPEDIA_NAMESPACE_ID_TO_NAME[training_data.page_namespace]
        ET.SubElement(common, "namespace").text = namespace.capitalize()
        ET.SubElement(common, "creator").text = training_data.page_creator
        ET.SubElement(common, "num_recent_edits").text = str(training_data.page_num_recent_edits)
        ET.SubElement(common, "num_recent_reversions").text = str(training_data.page_num_recent_reverts)

        current = ET.SubElement(wp_edit, "current")
        ET.SubElement(current, "minor").text = "true" if current_revision.is_minor else "false"
        ET.SubElement(current, "timestamp").text = str(current_revision.timestamp)
        ET.SubElement(current, "text").text = current_revision.text.decode("utf-8")

        previous = ET.SubElement(wp_edit, "previous")
        if previous_revision:
            ET.SubElement(previous, "timestamp").text = str(previous_revision.timestamp)
            ET.SubElement(previous, "text").text = previous_revision.text.decode("utf-8")

        review_interface = ET.SubElement(wp_edit, "ReviewInterface")
        ET.SubElement(review_interface, "status").text = edit.get_status_display()
        if edit.status == 2:
            ET.SubElement(wp_edit, "isVandalism").text = "true" if edit.classification == 0 else "false"
            ET.SubElement(review_interface, "reviewers").text = str(edit.number_of_reviewers)
            ET.SubElement(review_interface, "reviewers_agreeing").text = str(edit.number_of_agreeing_reviewers)

        try:
            score_data = ScoreData.objects.get(edit=edit)
        except ScoreData.DoesNotExist:
            logger.debug(f"Skipping inclusion of scores in WPEdit for {edit.id} due to no data")
        else:
            core_scores = ET.SubElement(wp_edit, "core_scores")
            if score_data.reverted:
                ET.SubElement(core_scores, "reverted").text = str(score_data.reverted)
            if score_data.training:
                ET.SubElement(core_scores, "training").text = str(score_data.training)

        return self._xml_to_string(wp_edit, indent_block)
