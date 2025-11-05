import logging
import socket
from typing import Optional
from xml.etree import ElementTree

from django.conf import settings

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.models import Edit

logger = logging.getLogger(__name__)


class Core:
    def score_edit(self, edit: Edit) -> Optional[float]:
        dumper = EditSetDumper()
        wp_edit = dumper.generate_wp_edit(edit)
        if not wp_edit:
            logger.error(f"[{edit.id}] Failed to generate wp_edit")
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((settings.CORE_HOST, settings.CORE_PORT))
            s.sendall(f'<?xml version="1.0"?>\n<WPEditSet>\n{wp_edit}\n</WPEditSet>'.encode("utf-8"))

            response = ""
            while True:
                data = s.recv(1024).decode("utf-8")
                if data == "":
                    break
                response += data

        logger.debug(f"[{edit.id}] Core returned: {response}")
        try:
            et = ElementTree.fromstring(response)
        except ElementTree.ParseError as e:
            logger.error(f"[{edit.id}] Core response could not be parsed: {response}: {e}")
            return

        return float(et.find("./WPEdit/score").text)
