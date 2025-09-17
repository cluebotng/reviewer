import logging
from datetime import datetime
from typing import Optional, Tuple, List

import requests
from django.db import connections

logger = logging.getLogger(__name__)


class WikipediaReader:
    def has_revision_been_deleted(self, revision_id: int) -> bool:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Edit Metadata",
            },
            timeout=10,
            params={
                "format": "json",
                "action": "query",
                "revids": revision_id,
            },
        )
        r.raise_for_status()
        bad_revision_ids = {entry["revid"] for entry in r.json()["query"].get("badrevids", {}).values()}
        return revision_id in bad_revision_ids

    def get_user(self, username: str) -> Tuple[Optional[int], List[str]]:
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
                "usprop": "centralids|rights",
                "ususers": username,
            },
        )
        r.raise_for_status()
        data = r.json()

        if user_data := next(iter(data.get("query", {}).get("users", [])), None):
            return user_data.get("centralids", {}).get("CentralAuth"), user_data.get("rights", [])

        return None, []

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
