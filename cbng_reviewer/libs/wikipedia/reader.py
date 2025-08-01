import logging
from datetime import datetime
from typing import Optional

import requests
from django.db import connections

logger = logging.getLogger(__name__)


class WikipediaReader:
    def has_revision_been_deleted(self, revision_id: int) -> bool:
        # This is similar to get_page_revisions & get_edit_metadata but,
        # we explicitly check for the removal keys.
        # If this returns true we will start trashing data, so it is quite specific

        # First get the page title
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Edit Metadata",
            },
            timeout=10,
            params={
                "format": "json",
                "action": "query",
                "rawcontinue": 1,
                "prop": "revisions",
                "rvslots": "*",
                "revids": revision_id,
            },
        )
        r.raise_for_status()
        page_data = r.json()

        if "badrevids" in page_data.get("query", {}).keys():
            return True

        page_title = next(iter(page_data.get("query", {}).get("pages", {}).values()), {}).get("title")
        if not page_title:
            return True

        # Now get the revision data
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Check For Revision Deletion",
            },
            timeout=10,
            params={
                "format": "json",
                "action": "query",
                "prop": "revisions",
                "titles": page_title,
                "rvstartid": revision_id,
                "rvlimit": 2,
                "rvslots": "*",
                "rvprop": "user|content",
            },
        )
        r.raise_for_status()
        data = r.json()

        if "badrevids" in data.get("query", {}).keys():
            return True

        revisions = next(iter(data.get("query", {}).get("pages", {}).values()), {}).get("revisions", [])

        current_revision = next(iter(revisions[0]["slots"].values()), {})
        previous_revision = {}
        if len(revisions) > 1:
            previous_revision = next(iter(revisions[1]["slots"].values()), {})

        return any(
            [
                "texthidden" in previous_revision,
                "userhidden" in previous_revision,
                "suppressed" in previous_revision,
                "current_revision" in current_revision,
                "userhidden" in current_revision,
                "suppressed" in previous_revision,
            ]
        )

    def get_central_auth_user_id(self, username: str) -> Optional[int]:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Central Auth User ID",
            },
            timeout=10,
            params={
                "format": "json",
                "action": "query",
                "list": "users",
                "usprop": "centralids",
                "ususers": username,
            },
        )
        r.raise_for_status()
        data = r.json()

        if user_data := next(iter(data.get("query", {}).get("users", [])), None):
            return user_data.get("centralids", {}).get("CentralAuth")

        return None

    def get_sampled_edits(self, namespace_id: int, start: datetime, end: datetime, quantity: int):
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get Sampled Edits
                SELECT `rev_id` FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                WHERE
                `page_namespace` = %s
                AND
                `rev_timestamp` BETWEEN %s AND %s
                ORDER BY RAND()
                LIMIT %s
                """,
                [
                    namespace_id,
                    start.strftime("%Y%m%d%H%M%S"),
                    end.strftime("%Y%m%d%H%M%S"),
                    quantity,
                ],
            )

            return [row[0] for row in cursor.fetchall()]
