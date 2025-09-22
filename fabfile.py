import base64
import os
from pathlib import PosixPath
from typing import Optional, Dict, Any

from fabric import Connection, Config, task

TARGET_USER = os.environ.get("TARGET_USER", "cluebotng-review")
TOOL_DIR = PosixPath("/data/project") / TARGET_USER
IMAGE_NAMESPACE = f"tool-{TARGET_USER}"
IMAGE_TAG_REVIEWER = "reviewer"

c = Connection(
    "login.toolforge.org",
    config=Config(overrides={"sudo": {"user": f"tools.{TARGET_USER}", "prefix": "/usr/bin/sudo -ni"}}),
)


def _get_file_contents(file_name: str) -> str:
    with (PosixPath(__file__).parent / "configs" / file_name).open("r") as fh:
        return fh.read()


def _push_file_to_remote(file_name: str, replace_vars: Optional[Dict[str, Any]] = None):
    replace_vars = {} if replace_vars is None else replace_vars

    file_contents = _get_file_contents(file_name)

    for key, value in replace_vars.items():
        file_contents = file_contents.replace(f'{"{{"} {key} {"}}"}', value)

    encoded_contents = base64.b64encode(file_contents.encode("utf-8")).decode("utf-8")
    target_path = (TOOL_DIR / file_name).as_posix()
    c.sudo(f"bash -c \"base64 -d <<< '{encoded_contents}' > '{target_path}'\"")


def _update_jobs():
    _push_file_to_remote(
        "jobs.yaml",
        {"tool_dir": TOOL_DIR.as_posix()},
    )
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs load {(TOOL_DIR / 'jobs.yaml').as_posix()}")


@task()
def enable_admin_mode(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ADMIN_ONLY true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def disable_admin_mode(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ADMIN_ONLY false")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def enable_irc_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_IRC_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def disable_irc_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_IRC_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def enable_user_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_USER_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def disable_user_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_USER_MESSAGING false")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart cluebotng-reviewer")


@task()
def deploy_jobs(_ctx):
    _update_jobs()
