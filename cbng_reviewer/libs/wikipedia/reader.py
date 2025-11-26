import logging
from datetime import datetime
from typing import Optional

import requests
from django.db import connections

from cbng_reviewer.libs.models.wikipedia import CentralWikiUser, LocalWikiUser

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

    def get_central_user(
        self, username: Optional[str] = None, user_id: Optional[int] = None
    ) -> Optional[CentralWikiUser]:
        if not username and not user_id:
            raise ValueError("either username or user_id must be passed to get_central_user")

        params = {
            "format": "json",
            "action": "query",
            "meta": "globaluserinfo",
        }
        params |= {"guiuser": username} if username else {"guiid": user_id}

        # Note: We ask meta wiki as it 'owns' central auth
        r = requests.get(
            "https://meta.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Central Auth User Username",
            },
            timeout=10,
            params=params,
        )
        r.raise_for_status()
        data = r.json()

        if user_data := data.get("query", {}).get("globaluserinfo"):
            logger.debug(f"Retrieved central user data for {username}: {user_data}")
            if "missing" not in user_data:
                return CentralWikiUser(
                    username=user_data["name"],
                    id=user_data["id"],
                )
        return None

    def get_local_user(self, username: str) -> Optional[LocalWikiUser]:
        # Note: We ask enwiki specifically as we want the wiki specific rights, not global rights
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Local User",
            },
            timeout=10,
            params={
                "format": "json",
                "action": "query",
                "list": "users",
                "usprop": "rights|groups",
                "ususers": username,
            },
        )
        r.raise_for_status()
        data = r.json()

        if user_data := next(iter(data.get("query", {}).get("users", [])), None):
            logger.debug(f"Retrieved local user data for {username}: {user_data}")
            if "missing" not in user_data:
                return LocalWikiUser(
                    username=user_data["name"],
                    rights=user_data["rights"],
                    groups=user_data["groups"],
                )
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

    # This logic matches that used by the box
    def get_user_edit_count(self, username: str) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Edit Count
                SELECT COUNT(*) FROM `revision_userindex`
                JOIN `actor` ON `actor_id` = `rev_actor`
                WHERE
                `actor_name` = %s
                """,
                [
                    username,
                ],
            )
            if row := cursor.fetchone():
                return row[0]
        return None

    def get_user_warning_count(self, username: str) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Warning Count
                SELECT COUNT(*), comment_text FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                JOIN `comment` ON `rev_comment_id` = `comment_id`
                WHERE
                `page_namespace` = 3
                AND
                `page_title` = %s
                AND
                (
                    `comment_text` LIKE '%%warning%%'
                    OR
                    `comment_text` LIKE 'General note: Nonconstructive%%'
                )
                """,
                [
                    username.replace(" ", "_"),
                ],
            )
            if row := cursor.fetchone():
                return row[0]
        return None
