from __future__ import annotations

import json
from typing import Any, Dict, List

import requests


class RabbitMQApi:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Content-Type": "application/json"})

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/{path.lstrip('/')}"

    def get(self, path: str) -> Any:
        resp = self.session.get(self._url(path), timeout=self.timeout)
        self._raise(resp)
        return resp.json()

    def get_or_empty(self, path: str) -> List[Any]:
        resp = self.session.get(self._url(path), timeout=self.timeout)
        if resp.status_code == 404:
            return []
        self._raise(resp)
        return resp.json()

    def put(self, path: str, payload: Dict[str, Any] | None = None) -> None:
        data = "" if payload is None else json.dumps(payload)
        resp = self.session.put(self._url(path), data=data, timeout=self.timeout)
        self._raise(resp)

    def post(self, path: str, payload: Dict[str, Any]) -> None:
        resp = self.session.post(self._url(path), data=json.dumps(payload), timeout=self.timeout)
        self._raise(resp)

    @staticmethod
    def _raise(resp: requests.Response) -> None:
        if 200 <= resp.status_code < 300:
            return
        raise RuntimeError(
            f"RabbitMQ API error {resp.status_code}: {resp.text[:400]}"
        )
