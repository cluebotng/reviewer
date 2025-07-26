import base64
import os
from pathlib import PosixPath
from typing import Optional, Dict, Any

import requests
from fabric import Connection, Config, task


def _get_latest_release() -> str:
    """Return the latest release tag from GitHub"""
    return "main"
    r = requests.get("https://api.github.com/repos/cluebotng/reviewer/releases/latest")
    r.raise_for_status()
    return r.json()["tag_name"]


TARGET_USER = os.environ.get("TARGET_USER", "cluebotng-review")
TOOL_DIR = PosixPath("/data/project") / TARGET_USER
IMAGE_NAME = f"tool-{TARGET_USER}/tool-{TARGET_USER}:latest"

c = Connection(
    "login.toolforge.org",
    config=Config(overrides={"sudo": {"user": f"tools.{TARGET_USER}", "prefix": "/usr/bin/sudo -ni"}}),
)


def _push_file_to_remote(file_name: str, replace_vars: Optional[Dict[str, Any]] = None):
    replace_vars = {} if replace_vars is None else replace_vars

    with (PosixPath(__file__).parent / "configs" / file_name).open("r") as fh:
        file_contents = fh.read()

    for key, value in replace_vars.items():
        file_contents = file_contents.replace(f'{"{{"} {key} {"}}"}', value)

    encoded_contents = base64.b64encode(file_contents.encode("utf-8")).decode("utf-8")
    target_path = (TOOL_DIR / file_name).as_posix()
    c.sudo(f"bash -c \"base64 -d <<< '{encoded_contents}' > '{target_path}'\"")


@task()
def admin_mode_enable(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ADMIN_ONLY true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def admin_mode_disable(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars delete --yes-im-sure CBNG_ADMIN_ONLY")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def deploy(_ctx):
    """Deploy the current release."""
    latest_release = _get_latest_release()

    # Get database use
    database_user = c.sudo(
        f"awk '{'{'}if($1 == \"user\") print $3{'}'}' {TOOL_DIR / 'replica.my.cnf'}", hide="stdout"
    ).stdout.strip()

    # Jobs config
    _push_file_to_remote("service.template")
    _push_file_to_remote(
        "jobs.yaml", {"target_image": IMAGE_NAME, "database_user": database_user, "tool_dir": TOOL_DIR.as_posix()}
    )

    # Ensure logs dir exists
    c.sudo(f'mkdir -p {TOOL_DIR / "logs"}')

    # Build
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"build start "
        f"-L "
        f"--ref {latest_release} "
        f"https://github.com/cluebotng/reviewer.git"
    )

    # Migrate database
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"jobs run "
        f"--wait "
        f"--image {IMAGE_NAME} "
        f'--command "./manage.py migrate" migrate-database'
    )

    # Restart web service
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice " f"buildservice restart")

    # Ensure cron jobs are setup
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs " f'load {TOOL_DIR / "jobs.yaml"}')
