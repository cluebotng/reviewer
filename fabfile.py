import base64
import os
from pathlib import PosixPath
from typing import Optional, Dict, Any

import requests
from fabric import Connection, Config, task


def _get_latest_release(org: str, repo: str) -> str:
    """Return the latest release tag from GitHub"""
    r = requests.get(f"https://api.github.com/repos/{org}/{repo}/releases/latest")
    r.raise_for_status()
    return r.json()["tag_name"]


TARGET_RELEASE = os.environ.get("TARGET_RELEASE")
TARGET_USER = os.environ.get("TARGET_USER", "cluebotng-review")
TOOL_DIR = PosixPath("/data/project") / TARGET_USER
IMAGE_NAMESPACE = f"tool-{TARGET_USER}"
IMAGE_TAG_REVIEWER = "reviewer"
IMAGE_TAG_IRC_RELAY = "irc-relay"

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


def _build_irc_relay():
    """Update the IRC relay release."""
    latest_release = TARGET_RELEASE or _get_latest_release("cluebotng", "irc_relay")
    print(f"Moving irc-relay to {latest_release}")

    # Update the latest image to our target release
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        "build start -L "
        f"--ref {latest_release} "
        f"-i {IMAGE_TAG_IRC_RELAY} "
        "https://github.com/cluebotng/irc_relay.git"
    )


def _build_reviewer():
    """Update the reviewer release."""
    latest_release = TARGET_RELEASE or _get_latest_release("cluebotng", "reviewer")
    latest_release = "main"
    print(f"Moving reviewer to {latest_release}")

    # Build
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"build start -L "
        f"--ref {latest_release} "
        f"-i {IMAGE_TAG_REVIEWER} "
        "https://github.com/cluebotng/reviewer.git"
    )


def _update_jobs():
    # Get database use
    database_user = c.sudo(
        f"awk '{'{'}if($1 == \"user\") print $3{'}'}' {TOOL_DIR / 'replica.my.cnf'}", hide="stdout"
    ).stdout.strip()

    # Jobs config
    _push_file_to_remote(
        "service.template", {"image_namespace": IMAGE_NAMESPACE, "image_tag_reviewer": IMAGE_TAG_REVIEWER}
    )
    _push_file_to_remote(
        "jobs.yaml",
        {
            "image_namespace": IMAGE_NAMESPACE,
            "image_tag_reviewer": IMAGE_TAG_REVIEWER,
            "image_tag_irc_relay": IMAGE_TAG_IRC_RELAY,
            "database_user": database_user,
            "tool_dir": TOOL_DIR.as_posix(),
        },
    )

    # Ensure jobs are setup
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs load {TOOL_DIR / 'jobs.yaml'}")


def _restart():
    # Migrate database
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"jobs run "
        f"--wait "
        f"--image {IMAGE_NAMESPACE}/{IMAGE_TAG_REVIEWER}:latest "
        f'--command "./manage.py migrate" migrate-database'
    )

    # Restart web service
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart -r 4")

    # Restart worker
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart celery-worker")


@task()
def enable_admin_mode(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ADMIN_ONLY true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def disable_admin_mode(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ADMIN_ONLY false")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def enable_irc_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_IRC_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def disable_irc_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_IRC_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def enable_user_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_USER_MESSAGING true")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def disable_user_messaging(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge envvars create CBNG_ENABLE_USER_MESSAGING false")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")


@task()
def restart_review(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice buildservice restart")
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart celery-worker")


@task()
def restart_irc_relay(_ctx):
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart irc-relay")


@task()
def deploy_jobs(_ctx):
    _update_jobs()


@task()
def deploy_reviewer(_ctx):
    """Deploy the reviewer app."""
    _build_reviewer()
    _restart()


@task()
def deploy(_ctx):
    """Deploy the current release."""
    _build_irc_relay()
    _build_reviewer()
    _restart()
    _update_jobs()
