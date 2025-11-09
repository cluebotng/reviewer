import os
import sys
from pathlib import Path
from typing import Dict, Any

import yaml
from deepmerge import always_merger


def detect_if_running_in_test() -> bool:
    if len(sys.argv) >= 2 and sys.argv[0].endswith("manage.py") and sys.argv[1] == "test":
        return True

    if "PYTEST_VERSION" in os.environ:
        return True

    return False


def _load_yaml(path: Path) -> Dict[str, Any]:
    if path.is_file():
        with path.open("r") as fh:
            return yaml.load(fh, Loader=yaml.SafeLoader)
    return {}


def load_config(base_dir: Path, in_test: bool) -> Dict[str, Any]:
    # Defaults
    cfg = {
        "django": {
            "secret_key": os.environ.get("DJANGO_SECRET_KEY", "development do not use"),
            "debug": False,
        },
        "mysql": {
            "default": {
                "schema": os.environ.get("TOOL_DB_SCHEMA", "cbng_reviewer"),
                "host": os.environ.get("TOOL_DB_HOST", "localhost"),
                "port": 3306,
                "user": os.environ.get("TOOL_DB_USER", "cbng_reviewer"),
                "password": os.environ.get("TOOL_DB_PASSWORD"),
            },
            "replica": {
                "schema": os.environ.get("TOOL_REPLICA_SCHEMA", "enwiki_p"),
                "host": os.environ.get("TOOL_REPLICA_HOST", "enwiki.labsdb"),
                "port": 3306,
                "user": os.environ.get("TOOL_REPLICA_USER", "cbng_reviewer"),
                "password": os.environ.get("TOOL_REPLICA_PASSWORD"),
            },
        },
        "oauth": {
            "key": os.environ.get("OAUTH_KEY"),
            "secret": os.environ.get("OAUTH_SECRET"),
        },
        "wikipedia": {
            "username": os.environ.get("WIKIPEDIA_USERNAME"),
            "password": os.environ.get("WIKIPEDIA_PASSWORD"),
        },
        "cbng": {
            "admin_only": os.environ.get("CBNG_ADMIN_ONLY") == "true",
            "enable_irc_messaging": os.environ.get("CBNG_ENABLE_IRC_MESSAGING") == "true",
            "enable_user_messaging": os.environ.get("CBNG_ENABLE_USER_MESSAGING") == "true",
        },
        "irc_relay": {
            "host": os.environ.get("IRC_RELAY_HOST", "irc-relay"),
            "port": 9334,
            "use_http": True,
            "channel": {
                "admin": "#wikipedia-en-cbngreview",
                "feed": "#wikipedia-en-cbngreview-feed",
            },
        },
        "core": {
            "host": os.environ.get("CORE_HOST", "core.tool-cluebotng-review.svc.tools.local"),
            "port": 3565,
        },
        "report": {
            "host": os.environ.get("REDIS_HOST", "report-interface.tool-cluebotng.svc.tools.local"),
            "port": 8000,
        },
        "redis": {
            "host": os.environ.get("REDIS_HOST", "redis.tool-cluebotng-review.svc.tools.local"),
            "port": 6379,
            "db": 0,
            "password": os.environ.get("REDIS_PASSWORD"),
        },
    }

    if in_test:
        # Testing defaults
        cfg["mysql"]["default"] |= {"host": "127.0.0.1", "port": 3306}
        cfg["mysql"]["replica"] |= {"host": "127.0.0.1", "port": 3306}
        cfg["redis"] |= {"host": "127.0.0.1", "port": 6379}
        cfg["cbng"] |= {"enable_irc_messaging": False, "enable_user_messaging": False}

    else:
        # Load local settings if the file exists
        cfg = always_merger.merge(cfg, _load_yaml(base_dir / "config.yaml"))

    # Load override settings
    if runtime_cfg := os.environ.get("CBNG_REVIEWER_CONFIG"):
        cfg = always_merger.merge(cfg, _load_yaml(Path(runtime_cfg)))

    return cfg
