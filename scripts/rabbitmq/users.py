from __future__ import annotations

import os
import secrets
import string
from pathlib import Path
from typing import Dict, List

PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"


def generate_password(length: int = 24) -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def load_users_file(users_file: Path) -> Dict[str, str]:
    if not users_file.exists():
        return {}

    existing: Dict[str, str] = {}
    for line in users_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        username, password = line.split(":", 1)
        existing[username.strip()] = password.strip()
    return existing


def append_users_file(users_file: Path, generated_users: Dict[str, str]) -> None:
    if not generated_users:
        return

    users_file.parent.mkdir(parents=True, exist_ok=True)
    existing = load_users_file(users_file)

    lines: List[str] = []
    for username, password in generated_users.items():
        if username in existing:
            continue
        lines.append(f"{username}: {password}")

    if not lines:
        return

    with users_file.open("a", encoding="utf-8") as fh:
        if users_file.stat().st_size > 0:
            fh.write("\n")
        fh.write("\n".join(lines) + "\n")

    if os.name == "posix":
        os.chmod(users_file, 0o600)
