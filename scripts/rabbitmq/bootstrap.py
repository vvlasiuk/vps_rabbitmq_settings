from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

from .api import RabbitMQApi
from .models import Action, BootstrapSettings
from .topology import DEFAULT_TAGS, build_topology
from .users import generate_password


def enc(value: str) -> str:
    return quote(value, safe="")


def print_summary(actions: List[Action]) -> None:
    print("\nSummary:")
    counts: Dict[str, int] = {}
    for action in actions:
        counts[action.status] = counts.get(action.status, 0) + 1
        if action.status == "skipped":
            continue
        msg = f"- [{action.status.upper()}] {action.resource} {action.name}"
        if action.details:
            msg += f" ({action.details})"
        print(msg)

    print("\nTotals:")
    for key in sorted(counts.keys()):
        print(f"- {key}: {counts[key]}")


def bootstrap(
    config: Dict[str, Any],
    settings: BootstrapSettings,
    users_file: Path,
    check_only: bool,
) -> Tuple[List[Action], Dict[str, str]]:
    actions: List[Action] = []
    generated_users: Dict[str, str] = {}

    vhosts: List[Dict[str, Any]] = config["vhosts"]

    api = RabbitMQApi(
        settings.api_url,
        settings.username,
        settings.password,
    )

    # Health check and auth validation.
    overview = api.get("overview")
    actions.append(Action("info", "server", "overview", f"rabbitmq_version={overview.get('rabbitmq_version', 'unknown')}"))

    existing_vhosts = {item["name"] for item in api.get("vhosts")}
    users = {item["name"] for item in api.get("users")}

    for vhost_cfg in vhosts:
        vhost_name = vhost_cfg["name"]
        channels = vhost_cfg.get("channels", [])
        
        topology = build_topology(vhost_name, channels)

        if vhost_name in existing_vhosts:
            actions.append(Action("skipped", "vhost", vhost_name, "already exists"))
        else:
            if check_only:
                actions.append(Action("planned", "vhost", vhost_name, "will create"))
            else:
                api.put(f"vhosts/{enc(vhost_name)}")
                actions.append(Action("created", "vhost", vhost_name))
            existing_vhosts.add(vhost_name)

        for user_cfg in topology["users"]:
            username = user_cfg["name"]
            tags = user_cfg.get("tags", DEFAULT_TAGS)

            if username in users:
                actions.append(Action("skipped", "user", username, "already exists"))
                continue

            password = user_cfg.get("password") or generate_password()
            generated_users[username] = password

            if check_only:
                actions.append(Action("planned", "user", username, "will create with generated password"))
            else:
                api.put(
                    f"users/{enc(username)}",
                    {"password": password, "tags": tags},
                )
                actions.append(Action("created", "user", username))
                users.add(username)

        perms = api.get_or_empty(f"vhosts/{enc(vhost_name)}/permissions")
        existing_perms_by_user = {item["user"]: item for item in perms}
        for perm_cfg in topology["permissions"]:
            username = perm_cfg["user"]

            payload = {
                "configure": perm_cfg["configure"],
                "write": perm_cfg["write"],
                "read": perm_cfg["read"],
            }

            if username in existing_perms_by_user:
                existing = existing_perms_by_user[username]
                if (
                    existing.get("configure") == payload["configure"]
                    and existing.get("write") == payload["write"]
                    and existing.get("read") == payload["read"]
                ):
                    actions.append(Action("skipped", "permission", username, f"already set for vhost={vhost_name}"))
                    continue
                if check_only:
                    actions.append(Action("planned", "permission", username, f"will update for vhost={vhost_name}"))
                else:
                    api.put(f"permissions/{enc(vhost_name)}/{enc(username)}", payload)
                    actions.append(Action("updated", "permission", username, f"vhost={vhost_name}"))
                continue

            if check_only:
                actions.append(Action("planned", "permission", username, f"will set for vhost={vhost_name}"))
            else:
                api.put(f"permissions/{enc(vhost_name)}/{enc(username)}", payload)
                actions.append(Action("created", "permission", username, f"vhost={vhost_name}"))

        exchanges = {item["name"] for item in api.get_or_empty(f"exchanges/{enc(vhost_name)}")}
        for exchange_cfg in topology["exchanges"]:
            name = exchange_cfg["name"]
            if name in exchanges:
                actions.append(Action("skipped", "exchange", name, "already exists"))
                continue

            payload = {
                "type": exchange_cfg.get("type", "direct"),
                "durable": bool(exchange_cfg.get("durable", True)),
                "auto_delete": bool(exchange_cfg.get("auto_delete", False)),
                "internal": bool(exchange_cfg.get("internal", False)),
                "arguments": exchange_cfg.get("arguments", {}),
            }
            if check_only:
                actions.append(Action("planned", "exchange", name, "will create"))
            else:
                api.put(f"exchanges/{enc(vhost_name)}/{enc(name)}", payload)
                actions.append(Action("created", "exchange", name))
                exchanges.add(name)

        queues = {item["name"] for item in api.get_or_empty(f"queues/{enc(vhost_name)}")}
        for queue_cfg in topology["queues"]:
            name = queue_cfg["name"]
            if name in queues:
                actions.append(Action("skipped", "queue", name, "already exists"))
                continue

            payload = {
                "durable": bool(queue_cfg.get("durable", True)),
                "auto_delete": bool(queue_cfg.get("auto_delete", False)),
                "arguments": queue_cfg.get("arguments", {}),
            }
            if check_only:
                actions.append(Action("planned", "queue", name, "will create"))
            else:
                api.put(f"queues/{enc(vhost_name)}/{enc(name)}", payload)
                actions.append(Action("created", "queue", name))
                queues.add(name)

        for binding_cfg in topology["bindings"]:
            source = binding_cfg["source"]
            destination = binding_cfg["destination"]
            routing_key = binding_cfg.get("routing_key", "")
            arguments = binding_cfg.get("arguments", {})

            binding_list = api.get_or_empty(
                f"bindings/{enc(vhost_name)}/e/{enc(source)}/q/{enc(destination)}"
            )
            exists = any(
                item.get("routing_key", "") == routing_key
                and (item.get("arguments") or {}) == arguments
                for item in binding_list
            )

            binding_name = f"{source}->{destination}:{routing_key or '<empty>'}"
            if exists:
                actions.append(Action("skipped", "binding", binding_name, "already exists"))
                continue

            payload = {
                "routing_key": routing_key,
                "arguments": arguments,
            }
            if check_only:
                actions.append(Action("planned", "binding", binding_name, "will create"))
            else:
                api.post(f"bindings/{enc(vhost_name)}/e/{enc(source)}/q/{enc(destination)}", payload)
                actions.append(Action("created", "binding", binding_name))

    return actions, generated_users
