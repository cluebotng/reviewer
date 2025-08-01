import logging

import requests
from django.conf import settings

from cbng_reviewer.libs.models.message import Message

logger = logging.getLogger(__name__)


class WikipediaManagement:
    def __init__(self, require_authentication: bool = True):
        self._session = requests.session()

        if settings.WIKIPEDIA_USERNAME and settings.WIKIPEDIA_PASSWORD:
            self._login(settings.WIKIPEDIA_USERNAME, settings.WIKIPEDIA_PASSWORD)
        elif require_authentication:
            raise ValueError("Missing credentials to enable authentication")

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

    def _login(self, username: str, password: str):
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
