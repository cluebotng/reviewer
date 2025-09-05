import logging
from typing import Set

import requests
from django.conf import settings

from cbng_reviewer import tasks
from cbng_reviewer.models import EditGroup, Edit

logger = logging.getLogger(__name__)


class ReportInterface:
    def fetch_edit_ids_requiring_review(self, include_in_progress: bool) -> Set[id]:
        r = requests.get(
            "https://cluebotng.toolforge.org/api/?action=review.export",
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Report Interface Fetch",
            },
            params={"include_in_progress": True} if include_in_progress else {},
        )
        r.raise_for_status()
        return set(r.json())

    def create_entries_for_reported_edits(self, include_in_progress: bool = False):
        edit_group, _ = EditGroup.objects.get_or_create(name=settings.CBNG_REPORT_EDIT_SET)
        for edit_id in self.fetch_edit_ids_requiring_review(include_in_progress):
            edit, created = Edit.objects.get_or_create(id=edit_id)
            edit.classification = 1

            if created:
                logger.info(f"Created edit {edit.id}, adding to {edit_group.name}")
                edit.groups.add(edit_group)

            elif not edit.groups.filter(pk=edit_group.pk).exists():
                logger.info(f"Adding edit {edit.id} to {edit_group.name}")
                edit.groups.add(edit_group)

            else:
                logger.debug(f"Edit {edit.id} already exists if target group")

            edit.save()
