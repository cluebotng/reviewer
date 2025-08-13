import base64
import json
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


EMIT_LOG_MESSAGES = os.environ.get("EMIT_LOG_MESSAGES", "true") == "true"
TARGET_RELEASE = os.environ.get("TARGET_RELEASE")
TARGET_USER = os.environ.get("TARGET_USER", "cluebotng-review")
TOOL_DIR = PosixPath("/data/project") / TARGET_USER
IMAGE_NAMESPACE = f"tool-{TARGET_USER}"
IMAGE_TAG_REVIEWER = "reviewer"
IMAGE_TAG_IRC_RELAY = "irc-relay"
IMAGE_TAG_GRAFANA_ALLOY = "grafana-alloy"

c = Connection(
    "login.toolforge.org",
    config=Config(overrides={"sudo": {"user": f"tools.{TARGET_USER}", "prefix": "/usr/bin/sudo -ni"}}),
)


def _get_file_contents(file_name: str) -> str:
    if file_name.startswith("."):
        file_name = file_name.lstrip(".")
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


def _do_log_message(message: str):
    """Emit a log message (from the tool account)."""
    c.sudo(f"{'' if EMIT_LOG_MESSAGES else 'echo '}dologmsg '{message}'")


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
    return latest_release


def _build_grafana_alloy():
    """Update the Grafana Alloy release."""
    target_release = _get_latest_release("cluebotng", "external-grafana-alloy")
    print(f"Moving grafana-alloy to {target_release}")

    # Update the latest image to our target release
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        "build start -L "
        f"--ref {target_release} "
        f"-i {IMAGE_TAG_GRAFANA_ALLOY} "
        "https://github.com/cluebotng/external-grafana-alloy.git"
    )


def _build_reviewer():
    """Update the reviewer release."""
    latest_release = TARGET_RELEASE or _get_latest_release("cluebotng", "reviewer")
    print(f"Moving reviewer to {latest_release}")

    # Build
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"build start -L "
        f"--ref {latest_release} "
        f"-i {IMAGE_TAG_REVIEWER} "
        "https://github.com/cluebotng/reviewer.git"
    )
    return latest_release


def _update_jobs():
    # Get database use
    database_user = c.sudo(
        f"awk '{'{'}if($1 == \"user\") print $3{'}'}' {(TOOL_DIR / 'replica.my.cnf').as_posix()}", hide="stdout"
    ).stdout.strip()

    # Webservice config
    _push_file_to_remote("service.template")
    _push_file_to_remote(".lighttpd.conf")

    # Jobs config
    _push_file_to_remote(
        "jobs.yaml",
        {
            "image_namespace": IMAGE_NAMESPACE,
            "image_tag_reviewer": IMAGE_TAG_REVIEWER,
            "image_tag_irc_relay": IMAGE_TAG_IRC_RELAY,
            "image_tag_grafana_alloy": IMAGE_TAG_GRAFANA_ALLOY,
            "database_user": database_user,
            "tool_dir": TOOL_DIR.as_posix(),
        },
    )

    # Ensure jobs are setup
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} echo toolforge jobs load {(TOOL_DIR / 'jobs.yaml').as_posix()}")


def _restart():
    # Migrate database
    c.sudo(
        f"XDG_CONFIG_HOME={TOOL_DIR} toolforge "
        f"jobs run "
        f"--wait "
        f"--image {IMAGE_NAMESPACE}/{IMAGE_TAG_REVIEWER}:latest "
        f'--command "launcher ./manage.py migrate" migrate-database'
    )

    # Ensure web service is running
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice start")

    # Restart worker
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs restart celery-worker")


# Temp
def _hack_irc_relay():
    """Patch kubernetes objects for UDP ports [T400024]."""
    service = json.loads(
        c.sudo(
            "kubectl get service irc-relay -ojson",
            hide="stdout",
        )
        .stdout.strip()
        .strip("'")
        .strip('"')
    )

    service["spec"]["ports"] = [
        port | {"protocol": "UDP"} for port in service["spec"]["ports"]
    ]

    encoded_contents = base64.b64encode(json.dumps(service).encode("utf-8")).decode(
        "utf-8"
    )
    c.sudo(f'bash -c "base64 -d <<<{encoded_contents} | kubectl apply -f-"')

    deployment = json.loads(
        c.sudo(
            "kubectl get deployment irc-relay -ojson",
            hide="stdout",
        )
        .stdout.strip()
        .strip("'")
        .strip('"')
    )

    deployment["spec"]["template"]["spec"]["containers"][0]["ports"] = [
        port | {"protocol": "UDP"}
        for port in deployment["spec"]["template"]["spec"]["containers"][0]["ports"]
    ]

    deployment["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = None
    deployment["spec"]["template"]["spec"]["containers"][0]["startupProbe"] = None

    encoded_contents = base64.b64encode(json.dumps(deployment).encode("utf-8")).decode(
        "utf-8"
    )
    c.sudo(f'bash -c "base64 -d <<<{encoded_contents} | kubectl apply -f-"')


def _hack_kubernetes_objects():
    """Deal with direct kubernetes objects [T400940]."""
    irc_relay_network_policy = _get_file_contents("network-policy.yaml")

    encoded_contents = base64.b64encode(irc_relay_network_policy.encode("utf-8")).decode("utf-8")
    c.sudo(f'bash -c "base64 -d <<<{encoded_contents} | kubectl apply -f-"')


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
    _hack_irc_relay()
    _hack_kubernetes_objects()


@task()
def deploy_reviewer(_ctx):
    """Deploy the reviewer app."""
    target_release = _build_reviewer()
    _restart()
    _do_log_message(f"reviewer deployed @ {target_release}")


@task()
def deploy(_ctx):
    """Deploy the current release."""
    _build_irc_relay()
    _build_reviewer()
    _restart()
    _update_jobs()
