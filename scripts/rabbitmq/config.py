from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import BootstrapSettings


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    vhosts_raw = config.get("vhosts")
    if vhosts_raw is None:
        single_vhost = str(config.get("vhost", "")).strip()
        if not single_vhost:
            raise ValueError("Missing required key in config: vhosts (or legacy vhost)")
        vhosts = [{"name": single_vhost, "channels": []}]
    else:
        if not isinstance(vhosts_raw, list) or not vhosts_raw:
            raise ValueError("Key vhosts must be a non-empty list")
        
        vhosts: List[Dict[str, Any]] = []
        for item in vhosts_raw:
            if isinstance(item, str):
                # Legacy format: plain string
                vhost_name = item.strip()
                if vhost_name:
                    vhosts.append({"name": vhost_name, "channels": []})
            elif isinstance(item, dict):
                # New format: dict with "name" and optional "channels"
                vhost_name = item.get("name", "").strip()
                if not vhost_name:
                    raise ValueError("Each vhost entry must have a 'name' field")
                channels = item.get("channels", [])
                if not isinstance(channels, list):
                    raise ValueError(f"'channels' must be a list for vhost '{vhost_name}'")
                # Validate channels are non-empty strings
                channels = [ch.strip() for ch in channels if isinstance(ch, str) and ch.strip()]
                vhosts.append({"name": vhost_name, "channels": channels})
            else:
                raise ValueError(f"Invalid vhost entry: {item}. Must be string or dict with 'name'")
        
        if not vhosts:
            raise ValueError("Key vhosts must contain at least one non-empty name")
    
    # Preserve order while removing duplicates (by vhost name)
    seen = set()
    unique_vhosts = []
    for vhost in vhosts:
        vhost_name = vhost["name"]
        if vhost_name not in seen:
            unique_vhosts.append(vhost)
            seen.add(vhost_name)
    
    config["vhosts"] = unique_vhosts

    return config


def load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_bootstrap_settings(args: argparse.Namespace) -> BootstrapSettings:
    load_env_file(Path(args.env_file))

    api_url = args.api_url or os.getenv("RABBITMQ_API_URL") or "http://127.0.0.1:15672"
    username = args.api_user or os.getenv("RABBITMQ_API_USER")
    password = args.api_password or os.getenv("RABBITMQ_API_PASSWORD")

    if not username:
        raise ValueError("API user is required. Use --api-user or RABBITMQ_API_USER")
    if not password:
        raise ValueError("API password is required. Use --api-password or RABBITMQ_API_PASSWORD")

    return BootstrapSettings(api_url=api_url, username=username, password=password)
