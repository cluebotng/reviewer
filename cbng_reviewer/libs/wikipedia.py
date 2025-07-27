import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import requests
from django.conf import settings
from django.db import connections

from cbng_reviewer.libs.models.message import Message
from cbng_reviewer.libs.models.wikipedia import (
    WikipediaEdit,
    WikipediaRevision,
    WikipediaPage,
)
from cbng_reviewer.models import Edit, TrainingData, Revision

logger = logging.getLogger(__name__)


class Wikipedia:
    _RE_NS_PREFIX = re.compile(rf'^({"|".join(settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID.keys())}):', re.IGNORECASE)

    def __init__(self, require_authentication: bool = False, skip_authenticate: bool = False):
        self._session = requests.session()
        if not skip_authenticate and settings.WIKIPEDIA_USERNAME and settings.WIKIPEDIA_PASSWORD:
            self.login(settings.WIKIPEDIA_USERNAME, settings.WIKIPEDIA_PASSWORD)
        elif require_authentication:
            raise ValueError("Asked to authenticate but no credentials")

    def _clean_page_title(self, title: str) -> str:
        title = self._RE_NS_PREFIX.sub("", title)
        title = title.replace(" ", "_")
        return title

    def _get_csrf_token(self):
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch CSRF Token",
            },
            params={
                "format": "json",
                "action": "query",
                "meta": "tokens",
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("query", {}).get("tokens", {}).get("csrftoken")

    def _get_login_token(self):
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Login Token",
            },
            params={
                "format": "json",
                "action": "query",
                "meta": "tokens",
                "type": "login",
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("query", {}).get("tokens", {}).get("logintoken")

    def has_revision_been_deleted(self, revision_id: int) -> bool:
        # This is similar to get_page_revisions & get_edit_metadata but,
        # we explicitly check for the removal keys.
        # If this returns true we will start trashing data, so it is quite specific

        # First get the page title
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Edit Metadata",
            },
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
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Check For Revision Deletion",
            },
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
        if len(revisions) == 1:
            previous_revision = {}
            current_revision = revisions[0]
        else:
            previous_revision = revisions[0]
            current_revision = revisions[1]

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

    def update_statistics_page(self, content: str):
        r = self._session.post(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Update Review Statistics Page",
            },
            data={
                "format": "json",
                "action": "edit",
                "title": "User:ClueBot NG/ReviewInterface/Stats",
                "summary": "Uploading Stats",
                "token": self._get_csrf_token(),
                "text": content,
            },
        )
        r.raise_for_status()

    def send_user_message(self, username: str, message: Message) -> bool:
        if not message.subject or not message.body:
            logger.warning(f"Skipping user email due to missing subject or body: {message}")
            return False
        return self._send_user_email(username, message.subject, message.body)

    def _send_user_email(self, username: str, subject: str, content: str) -> bool:
        if not settings.CBNG_ENABLE_USER_MESSAGING:
            logger.debug(f"Skipping sending email to {username} ({subject})")
            return False

        r = self._session.post(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Send User Email",
            },
            data={
                "format": "json",
                "action": "emailuser",
                "target": username,
                "subject": subject,
                "text": content,
                "token": self._get_csrf_token(),
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("emailuser", {}).get("result") == "Success"

    def fetch_user_central_id(self, username: str) -> Optional[int]:
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Central User ID",
            },
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

    def login(self, username: str, password: str):
        r = self._session.post(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Login",
            },
            data={
                "format": "json",
                "action": "login",
                "lgname": username,
                "lgpassword": password,
                "lgtoken": self._get_login_token(),
            },
        )
        r.raise_for_status()

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

    # These functions are similar to those in https://github.com/cluebotng/bot/blob/main/mysql_functions.php,
    # however we gate the upper bound of time to the time of an edit.
    #
    # This should provide a somewhat consistent view as to what the bot would have seen at the time the edit
    # was (roughly) processed.

    def get_edit_metadata(self, revision_id: int) -> Optional[WikipediaEdit]:
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Edit Metadata",
            },
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
            return None

        page_data = next(iter(data.get("query", {}).get("pages", {}).values()), None)
        if not page_data:
            logger.warning(f"Found no pages for {revision_id}")
            return None

        return WikipediaEdit(
            title=page_data["title"],
            namespace=settings.WIKIPEDIA_NAMESPACE_ID_TO_NAME[page_data["ns"]],
            timestamp=datetime.fromisoformat(page_data["revisions"][0]["timestamp"]),
        )

    def _is_revision_minor(self, revision: Dict[str, Any]) -> bool:
        minor = revision.get("minor", False)
        if minor == "":
            minor = False
        return minor

    def get_page_revisions(
        self, page_title: str, revision_id: int
    ) -> Tuple[Optional[WikipediaRevision], Optional[WikipediaRevision]]:
        r = self._session.get(
            "https://en.wikipedia.org/w/api.php",
            headers={
                "User-Agent": "ClueBot NG Reviewer - Wikipedia - Fetch Page Revisions",
            },
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
            return None, None

        revisions = [
            revision
            for revision in page_data.get("revisions", [])
            if "texthidden" not in revision and "userhidden" not in revision
        ]
        if not revisions:
            logger.warning(f"Missing revisions for {revision_id}")
            return None, None

        current_revision, previous_revision = None, None
        if len(revisions) == 1:
            current_offset = 1
        else:
            current_offset = 0

            if text := next(iter(revisions[1]["slots"].values()), {}).get("*"):
                previous_revision = WikipediaRevision(
                    timestamp=datetime.fromisoformat(revisions[1]["timestamp"]),
                    user=revisions[1]["user"],
                    minor=self._is_revision_minor(revisions[1]),
                    comment=revisions[1]["comment"],
                    text=text,
                )

        if text := next(iter(revisions[current_offset]["slots"].values()), {}).get("*"):
            current_revision = WikipediaRevision(
                timestamp=datetime.fromisoformat(revisions[current_offset]["timestamp"]),
                user=revisions[current_offset]["user"],
                minor=self._is_revision_minor(revisions[current_offset]),
                comment=revisions[current_offset]["comment"],
                text=text,
            )

        return current_revision, previous_revision

    def fetch_edit(self, revision_id: int) -> Optional[WikipediaEdit]:
        if edit := self.get_edit_metadata(revision_id):
            current, previous = self.get_page_revisions(edit.title, revision_id)
            if current:
                edit.current_revision = current
                edit.previous_revision = previous
                return edit
        return None

    def get_page_creation_metadata(self, page_title: str, namespace: str) -> Optional[WikipediaPage]:
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
                return WikipediaPage(
                    creation_time=datetime.strptime(row[0].decode("utf-8"), "%Y%m%d%H%M%S"),
                    creation_user=row[1].decode("utf-8"),
                )
            return None

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
            return None

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
            return None

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
            return None

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
            return None

    def get_user_registration_time(self, username: str) -> Optional[int]:
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
            return None

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
            return None

    def create_training_data_for_edit(self, edit: Edit):
        wikipedia_edit = self.fetch_edit(edit.id)
        if wikipedia_edit is None:
            logger.error(f"Failed to fetch edit data for {edit.id}")
            return

        if not wikipedia_edit.current_revision:
            logger.error(f"Failed to fetch revision data for {wikipedia_edit.title} ({edit.id}")
            return

        page_metadata = self.get_page_creation_metadata(wikipedia_edit.title, wikipedia_edit.namespace)
        if page_metadata is None:
            logger.error(f"Failed to fetch page metadata for {wikipedia_edit.title} ({edit.id})")
            return

        user_registration_time = self.get_user_registration_time(wikipedia_edit.current_revision.user)
        if user_registration_time is None:
            logger.error(
                f"Failed to fetch user registration time for {wikipedia_edit.current_revision.user} ({edit.id})"
            )
            return

        user_edit_count = self.get_user_edit_count(wikipedia_edit.current_revision.user, wikipedia_edit.timestamp)
        if user_edit_count is None:
            logger.error(f"Failed to fetch edit count for {wikipedia_edit.current_revision.user} ({edit.id})")
            return

        user_distinct_pages_count = self._get_user_distinct_pages_count(
            wikipedia_edit.current_revision.user, wikipedia_edit.timestamp
        )
        if user_distinct_pages_count is None:
            logger.error(f"Failed to fetch distinct count for {wikipedia_edit.current_revision.user} ({edit.id})")
            return

        user_warns_count = self.get_user_warning_count(wikipedia_edit.current_revision.user, wikipedia_edit.timestamp)
        if user_warns_count is None:
            logger.error(f"Failed to fetch warn count for {wikipedia_edit.current_revision.user} ({edit.id})")
            return

        page_num_recent_edits = self.get_page_recent_edit_count(
            wikipedia_edit.title, wikipedia_edit.namespace, wikipedia_edit.timestamp
        )
        if page_num_recent_edits is None:
            logger.error(f"Failed to fetch recent page edit count for {wikipedia_edit.title} ({edit.id})")
            return

        page_num_recent_reverts = self.get_page_recent_revert_count(
            wikipedia_edit.title, wikipedia_edit.namespace, wikipedia_edit.timestamp
        )
        if page_num_recent_reverts is None:
            logger.error(f"Failed to fetch recent page revert count for {wikipedia_edit.title} ({edit.id})")
            return

        TrainingData.objects.filter(edit=edit).delete()
        TrainingData.objects.create(
            edit=edit,
            timestamp=wikipedia_edit.timestamp.strftime("%s"),
            comment=wikipedia_edit.current_revision.comment,
            user=wikipedia_edit.current_revision.user,
            user_edit_count=user_edit_count,
            user_distinct_pages=user_distinct_pages_count,
            user_warns=user_warns_count,
            user_reg_time=user_registration_time.strftime("%s"),
            prev_user=wikipedia_edit.previous_revision.user if wikipedia_edit.previous_revision else None,
            page_title=wikipedia_edit.title,
            page_namespace=settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[wikipedia_edit.namespace.lower()],
            page_created_time=page_metadata.creation_time.strftime("%s"),
            page_creator=page_metadata.creation_user,
            page_num_recent_edits=page_num_recent_edits,
            page_num_recent_reverts=page_num_recent_reverts,
        )

        Revision.objects.filter(edit=edit).delete()
        if wikipedia_edit.current_revision:
            Revision.objects.create(
                edit=edit,
                type=0,
                minor=wikipedia_edit.current_revision.minor,
                timestamp=wikipedia_edit.current_revision.timestamp.strftime("%s"),
                text=wikipedia_edit.current_revision.text.encode("utf-8"),
            )
        if wikipedia_edit.previous_revision:
            Revision.objects.create(
                edit=edit,
                type=1,
                minor=wikipedia_edit.previous_revision.minor,
                timestamp=wikipedia_edit.previous_revision.timestamp.strftime("%s"),
                text=wikipedia_edit.previous_revision.text.encode("utf-8"),
            )
