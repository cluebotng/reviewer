from pathlib import PosixPath
from fabric import Connection, Config, task

TOOL_USER = "cluebotng-review"
TOOL_DIR = PosixPath("/data/project") / TOOL_USER

c = Connection(
    "login.toolforge.org",
    config=Config(overrides={"sudo": {"user": f"tools.{TOOL_USER}", "prefix": "/usr/bin/sudo -ni"}}),
)


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
