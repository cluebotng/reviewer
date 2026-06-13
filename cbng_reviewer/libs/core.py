import logging
import socket
import xml.etree.ElementTree as ET  # nosec: B405

from django.conf import settings

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.models import Edit

logger = logging.getLogger(__name__)


class Core:
    def __init__(self, target_host: str = settings.CORE_HOST, target_port: int = settings.CORE_PORT):
        self._target_host = target_host
        self._target_port = target_port
        self._dumper = EditSetDumper()

    def score_edit(self, edit: Edit, wp_edit: str | None = None) -> tuple[bool | None, float | None]:
        if wp_edit is None:
            wp_edit = self._dumper.generate_wp_edit(edit)

        if not wp_edit:
            logger.error(f"[{edit.id}] Failed to generate wp_edit")
            return None, None

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self._target_host, self._target_port))
            s.sendall(f'<?xml version="1.0"?>\n<WPEditSet>\n{wp_edit}\n</WPEditSet>'.encode("utf-8"))

            response = ""
            while True:
                data = s.recv(1024).decode("utf-8")
                if data == "":
                    break
                response += data

        logger.debug(f"[{edit.id}] Core returned: {response}")
        try:
            et = ET.fromstring(response)  # nosec: B314
        except ET.ParseError as e:
            logger.error(f"[{edit.id}] Core response could not be parsed: {response}: {e}")
            return None, None

        return et.find("./WPEdit/think_vandalism").text == "true", float(et.find("./WPEdit/score").text)
