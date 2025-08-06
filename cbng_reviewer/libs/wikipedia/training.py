import logging
import re
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import requests
from django.conf import settings
from django.db import connections

from cbng_reviewer.libs.models.edit_set import WpEdit, WpRevision
from cbng_reviewer.models import Edit

logger = logging.getLogger(__name__)


# These functions are similar to those in https://github.com/cluebotng/bot/blob/main/mysql_functions.php,
# however we gate the upper bound of time to the time of an edit.
#
# This should provide a somewhat consistent view as to what the bot would have seen at the time the edit
# was (roughly) processed.
class WikipediaTraining:
    _RE_NS_PREFIX = re.compile(rf'^({"|".join(settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID.keys())}):', re.IGNORECASE)

    def _clean_page_title(self, title: str) -> str:
        title = self._RE_NS_PREFIX.sub("", title)
        title = title.replace(" ", "_")
        return title

    def get_edit_metadata(self, revision_id: int) -> Tuple[Optional[str], Optional[str]]:
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
                "rvprop": "timestamp",
            },
        )
        r.raise_for_status()
        data = r.json()

        if "badrevids" in data.get("query", {}).keys():
            logger.warning(f"Bad revision id {revision_id}")
            return None, None

        page_data = next(iter(data.get("query", {}).get("pages", {}).values()), None)
        if not page_data:
            logger.warning(f"Found no pages for {revision_id}")
            return None, None

        return page_data["title"], settings.WIKIPEDIA_NAMESPACE_ID_TO_NAME[page_data["ns"]]

    def _is_revision_minor(self, revision: Dict[str, Any]) -> bool:
        minor = revision.get("minor", False)
        if minor == "":
            minor = False
        return minor

    def get_page_revisions(self, page_title: str, revision_id: int) -> Tuple[WpRevision, WpRevision]:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Page Revisions",
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
                "rvprop": "user|content|flags|timestamp|comment",
            },
        )
        r.raise_for_status()
        data = r.json()

        page_data = next(iter(data.get("query", {}).get("pages", {}).values()), None)
        if not page_data:
            logger.warning(f"Found no pages for {revision_id}")
            return WpRevision(), WpRevision()

        revisions = [
            revision
            for revision in page_data.get("revisions", [])
            if "texthidden" not in revision and "userhidden" not in revision
        ]
        if not revisions:
            logger.warning(f"Missing revisions for {revision_id}")
            return WpRevision(), WpRevision()

        current_revision, previous_revision = WpRevision(), WpRevision()

        current_text = next(iter(revisions[0]["slots"].values()), {}).get("*")
        if current_text is not None:
            current_revision = WpRevision(
                timestamp=datetime.fromisoformat(revisions[0]["timestamp"]),
                user=revisions[0]["user"],
                minor=self._is_revision_minor(revisions[0]),
                comment=revisions[0].get("comment"),
                text=current_text,
            )

        if len(revisions) > 1:
            previous_text = next(iter(revisions[1]["slots"].values()), {}).get("*")
            if previous_text is not None:
                previous_revision = WpRevision(
                    timestamp=datetime.fromisoformat(revisions[1]["timestamp"]),
                    user=revisions[1]["user"],
                    minor=self._is_revision_minor(revisions[1]),
                    comment=revisions[1].get("comment"),
                    text=previous_text,
                )

        return current_revision, previous_revision

    def get_page_creation_metadata(self, page_title: str, namespace: str) -> Tuple[Optional[datetime], Optional[str]]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get Page Creation Metadata
                SELECT `rev_timestamp`, `actor_name` FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                JOIN `actor` ON `actor_id` = `rev_actor`
                WHERE
                `page_namespace` = %s
                AND
                `page_title` = %s
                ORDER BY `rev_id`
                LIMIT 1
                """,
                [
                    settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[namespace.lower()],
                    self._clean_page_title(page_title),
                ],
            )
            if row := cursor.fetchone():
                return datetime.strptime(row[0].decode("utf-8"), "%Y%m%d%H%M%S"), row[1].decode("utf-8")
        return None, None

    def get_page_recent_edit_count(self, page_title: str, namespace: str, edit_time: datetime) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get Page Recent Edit Count
                SELECT COUNT(*) as count FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                WHERE
                `page_namespace` = %s
                AND
                `page_title` = %s
                AND
                `rev_timestamp` > %s
                AND
                `rev_timestamp` <= %s
                """,
                [
                    settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[namespace.lower()],
                    self._clean_page_title(page_title),
                    (edit_time - timedelta(days=settings.CBNG_RECENT_EDIT_WINDOW_DAYS)).strftime(
                        "%Y%m%d%H%M%S"
                    ),  # 'Recent Change window'
                    edit_time.strftime("%Y%m%d%H%M%S"),
                ],
            )
            if row := cursor.fetchone():
                return row[0]

    def get_page_recent_revert_count(self, page_title: str, namespace: str, edit_time: datetime) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get Page Recent Revert Count
                SELECT COUNT(*) as count FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                JOIN `comment` ON `comment_id` = `rev_comment_id`
                WHERE
                `page_namespace` = %s
                AND
                `page_title` = %s
                AND
                `rev_timestamp` > %s
                AND
                `rev_timestamp` <= %s
                AND `comment_text` LIKE 'Revert%%'
                """,
                [
                    settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[namespace.lower()],
                    self._clean_page_title(page_title),
                    (edit_time - timedelta(days=settings.CBNG_RECENT_EDIT_WINDOW_DAYS)).strftime(
                        "%Y%m%d%H%M%S"
                    ),  # 'Recent Change window'
                    edit_time.strftime("%Y%m%d%H%M%S"),
                ],
            )
            if row := cursor.fetchone():
                return row[0]

    def get_user_edit_count(self, username: str, edit_time: datetime) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Edit Count
                SELECT COUNT(*) AS `user_editcount` FROM `revision_userindex`
                WHERE
                `rev_actor` = (SELECT actor_id FROM actor WHERE `actor_name` = %s)
                AND
                `rev_timestamp` <= %s
                """,
                [username, edit_time.strftime("%Y%m%d%H%M%S")],
            )
            if row := cursor.fetchone():
                return row[0]

    def get_user_warning_count(self, username: str, edit_time: datetime) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Warning Count
                SELECT COUNT(*) as count FROM `page`
                JOIN `revision` ON `rev_page` = `page_id`
                JOIN `comment` ON `comment_id` = `rev_comment_id`
                WHERE
                `page_namespace` = 3
                AND
                `page_title` = %s
                AND
                `rev_timestamp` <= %s
                AND
                (
                    `comment_text` LIKE '%%warning%%'
                    OR
                    `comment_text` LIKE 'General note: Nonconstructive%%'
                )
                """,
                [username, edit_time.strftime("%Y%m%d%H%M%S")],
            )
            if row := cursor.fetchone():
                return row[0]

    def get_user_registration_time(self, username: str) -> Optional[datetime]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Registration Time
                SELECT `rev_timestamp` FROM `revision_userindex`
                WHERE
                `rev_actor` = (SELECT actor_id FROM actor WHERE `actor_name` = %s)
                ORDER BY `rev_timestamp`
                LIMIT 1
                """,
                [username],
            )
            if row := cursor.fetchone():
                return datetime.strptime(row[0].decode("utf-8"), "%Y%m%d%H%M%S")

    def _get_user_distinct_pages_count(self, username: str, edit_time: datetime) -> Optional[int]:
        with connections["replica"].cursor() as cursor:
            cursor.execute(
                """
                -- ClueBot NG Reviewer - Wikipedia - Get User Distinct Pages Count
                SELECT COUNT(DISTINCT rev_page) AS count FROM `revision_userindex`
                WHERE
                `rev_actor` = (SELECT actor_id FROM actor WHERE `actor_name` = %s)
                AND
                `rev_timestamp` <= %s
                """,
                [username, edit_time.strftime("%Y%m%d%H%M%S")],
            )
            if row := cursor.fetchone():
                return row[0]

    def build_wp_edit(self, edit: Edit) -> WpEdit:
        wp_edit = WpEdit(edit_id=edit.id)
        page_title, page_namespace = self.get_edit_metadata(edit.id)
        wp_edit = replace(wp_edit, title=page_title, namespace=page_namespace)

        if wp_edit.title and wp_edit.namespace:
            page_created_at, page_created_by = self.get_page_creation_metadata(
                page_title=wp_edit.title, namespace=wp_edit.namespace
            )
            wp_edit = replace(wp_edit, creator=page_created_by, page_made_time=page_created_at)

            current_revision, previous_revision = self.get_page_revisions(page_title=wp_edit.title, revision_id=edit.id)
            if current_revision.has_complete_training_data:
                wp_edit = replace(wp_edit, current=current_revision)
            if previous_revision.has_complete_training_data:
                wp_edit = replace(wp_edit, previous=previous_revision)

        if wp_edit.current:
            wp_edit = replace(
                wp_edit,
                user=wp_edit.current.user,
                comment=wp_edit.current.comment,
                user_reg_time=self.get_user_registration_time(wp_edit.current.user),
                user_edit_count=self.get_user_edit_count(wp_edit.current.user, wp_edit.current.timestamp),
                user_distinct_pages=self._get_user_distinct_pages_count(
                    wp_edit.current.user, wp_edit.current.timestamp
                ),
                user_warns=self.get_user_warning_count(wp_edit.current.user, wp_edit.current.timestamp),
            )

        if wp_edit.title and wp_edit.namespace and wp_edit.current:
            wp_edit = replace(
                wp_edit,
                num_recent_edits=self.get_page_recent_edit_count(
                    wp_edit.title, wp_edit.namespace, wp_edit.current.timestamp
                ),
                num_recent_reversions=self.get_page_recent_revert_count(
                    wp_edit.title, wp_edit.namespace, wp_edit.current.timestamp
                ),
            )

        return wp_edit
