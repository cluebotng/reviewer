import logging
from typing import Set

import requests
from django.conf import settings

from cbng_reviewer.models import EditGroup, Edit

logger = logging.getLogger(__name__)


class ReportInterface:
    def fetch_edit_ids_requiring_review(self, include_in_progress: bool) -> Set[id]:
        r = requests.get(
            f"http://{settings.REPORT_HOST}:{settings.REPORT_PORT}/api/",
            params={"action": "review.export", "include_in_progress": include_in_progress},
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Report Interface Fetch",
            },
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

    def fetch_vandalism_score(self, edit_id: int) -> float | None:
        r = requests.get(
            f"http://{settings.REPORT_HOST}:{settings.REPORT_PORT}/api/",
            params={"action": "vandalism.get.score", "new_id": edit_id},
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Report Interface Fetch",
            },
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            if data["error"] == "No entry found in database":
                logger.debug(f"[{edit_id}] No vandalism entry found")
            else:
                logger.error(f"[{edit_id}] Failed to get score from report: {data}")
            return
        return data["score"]

    def create_report_for_edit(self, edit_id: int) -> float | None:
        # Use the score endpoint to resolve the revert id
        r = requests.get(
            f"http://{settings.REPORT_HOST}:{settings.REPORT_PORT}/api/",
            params={"action": "vandalism.get.score", "new_id": edit_id},
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Create Report For Edit",
            },
        )
        r.raise_for_status()
        revert_id = r.json()["id"]
        logger.info(f"Got revert id {revert_id} for {edit_id}")

        # Using the revert id, check if there is a report
        r = requests.get(
            f"http://{settings.REPORT_HOST}:{settings.REPORT_PORT}/api/",
            params={"action": "reports.get", "id": revert_id},
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Create Report For Edit",
            },
        )
        r.raise_for_status()
        data = r.json()
        if "error" not in data:
            logger.info(f"Report already exists for {revert_id}")
            return

        if data["error_message"] != "Specified id was not found":
            logger.error(f"Unknown error while checking for report {revert_id}: {data}")
            return

        # No report, create one!
        logger.info(f"Creating report for {revert_id}")
        r = requests.post(
            f"http://{settings.REPORT_HOST}:{settings.REPORT_PORT}/?page=Report",
            data={
                "id": revert_id,
                "submit": "1",
                "user": "ClueBot NG",
                "comment": "Temporary Account Bug",
            },
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Create Report For Edit",
            },
        )
        r.raise_for_status()

    def fetch_deferred_users(self) -> tuple[str, list[str]]:
        r = requests.get(
            "https://cluebotng.toolforge.org/api/",
            params={"action": "review.export.users"},
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Add Reviews From Report",
            },
        )
        r.raise_for_status()
        return tuple(r.json().items())
