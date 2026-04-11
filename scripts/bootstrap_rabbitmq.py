#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rabbitmq.bootstrap import bootstrap, print_summary
from rabbitmq.config import load_config, parse_bootstrap_settings
from rabbitmq.users import append_users_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RabbitMQ client bootstrap")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file with RabbitMQ API settings (default: .env)",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="RabbitMQ management API URL (default: env RABBITMQ_API_URL or http://127.0.0.1:15672)",
    )
    parser.add_argument(
        "--api-user",
        default=None,
        help="RabbitMQ management username (or env RABBITMQ_API_USER)",
    )
    parser.add_argument(
        "--api-password",
        default=None,
        help="RabbitMQ management password (or env RABBITMQ_API_PASSWORD)",
    )
    parser.add_argument(
        "--users-file",
        default="users",
        help="File where generated passwords for new users are saved",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run mode. Show planned actions only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    users_file = Path(args.users_file)

    try:
        config = load_config(config_path)
        settings = parse_bootstrap_settings(args)
        actions, generated_users = bootstrap(config, settings, users_file, args.check)

        if args.check:
            if generated_users:
                print(f"\nPlanned new users: {', '.join(sorted(generated_users.keys()))}")
            print("No changes were applied (--check).")
        else:
            append_users_file(users_file, generated_users)
            if generated_users:
                print(
                    "\nGenerated passwords were saved for users: "
                    f"{', '.join(sorted(generated_users.keys()))}"
                )

        print_summary(actions)
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
