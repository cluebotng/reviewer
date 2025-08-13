import base64
import json
import os
from pathlib import PosixPath
from typing import Optional, Dict, Any

from fabric import Connection, Config, task

TARGET_USER = os.environ.get("TARGET_USER", "cluebotng-review")
TOOL_DIR = PosixPath("/data/project") / TARGET_USER

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


def _update_jobs():
    # Get database user
    database_user = c.sudo(
        f"awk '{'{'}if($1 == \"user\") print $3{'}'}' {(TOOL_DIR / 'replica.my.cnf').as_posix()}", hide="stdout"
    ).stdout.strip()

    # Write the webservice config
    _push_file_to_remote("service.template")
    _push_file_to_remote(".lighttpd.conf")

    # Write the jobs config
    _push_file_to_remote("jobs.yaml", {"database_user": database_user, "tool_dir": TOOL_DIR.as_posix()})

    # Load the jobs config
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge jobs load {(TOOL_DIR / 'jobs.yaml').as_posix()}")


def _start_webservice():
    # Ensure web service (proxy layer) is running
    c.sudo(f"XDG_CONFIG_HOME={TOOL_DIR} toolforge webservice start")


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
def deploy_jobs(_ctx):
    _update_jobs()
    _start_webservice()
    _hack_irc_relay()
    _hack_kubernetes_objects()
