from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class BackendResult:
    ok: bool
    status_code: int
    detail: str


class MainBackendClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def send_entry_event(self, payload: dict) -> BackendResult:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

        try:
            response = httpx.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            return BackendResult(
                ok=response.is_success,
                status_code=response.status_code,
                detail=response.text,
            )
        except httpx.HTTPError as exc:
            return BackendResult(ok=False, status_code=0, detail=str(exc))
