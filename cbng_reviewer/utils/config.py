import os
from pathlib import Path
from typing import Dict, Any

import yaml
from deepmerge import always_merger


def _load_yaml(path: Path) -> Dict[str, Any]:
    if path.is_file():
        with path.open("r") as fh:
            return yaml.load(fh, Loader=yaml.SafeLoader)
    return {}


def load_config(base_dir: Path) -> Dict[str, Any]:
    # Defaults
    cfg = {
        "django": {
            "secret_key": os.environ.get("DJANGO_SECRET_KEY", "development do not use"),
            "debug": False,
        },
        "mysql": {
            "default": {
                "schema": os.environ.get("TOOL_TOOLSDB_SCHEMA", "cbng_reviewer"),
                "host": os.environ.get("TOOL_TOOLSDB_HOST", "tools-db"),
                "port": 3306,
                "user": os.environ.get("TOOL_TOOLSDB_USER", ""),
                "password": os.environ.get("TOOL_TOOLSDB_PASSWORD", ""),
            },
            "replica": {
                "schema": os.environ.get("TOOL_REPLICA_SCHEMA", "enwiki_p"),
                "host": os.environ.get("TOOL_REPLICA_HOST", "enwiki.labsdb"),
                "port": 3306,
                "user": os.environ.get("TOOL_REPLICA_USER", ""),
                "password": os.environ.get("TOOL_REPLICA_PASSWORD", ""),
            },
        },
        "oauth": {
            "key": os.environ.get("OAUTH_KEY", None),
            "secret": os.environ.get("OAUTH_SECRET", None),
        },
        "wikipedia": {
            "username": os.environ.get("WIKIPEDIA_USERNAME", None),
            "password": os.environ.get("WIKIPEDIA_PASSWORD", None),
        },
        "cbng": {
            "admin_only": os.environ.get("CBNG_ADMIN_ONLY", "") == "true",
        },
    }
    cfg = always_merger.merge(cfg, _load_yaml(base_dir / "config.yaml"))
    if runtime_cfg := os.environ.get("CBNG_REVIEWER_CONFIG"):
        cfg = always_merger.merge(cfg, _load_yaml(Path(runtime_cfg)))
    return cfg
