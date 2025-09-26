import logging
from pathlib import PosixPath

import requests

logger = logging.getLogger(__name__)


def download_file(
    target: PosixPath,
    url: str,
    timeout: int = 10,
    chunk_size: int = 512,
    user_agent: str = "ClueBot NG Reviewer - Download File",
):
    r = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": user_agent,
        },
        stream=True,
    )
    r.raise_for_status()
    with target.open("wb") as fh:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fh.write(chunk)
