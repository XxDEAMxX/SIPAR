import logging
from typing import Any

import httpx


logger = logging.getLogger("vehicle-entry-service")


class BackendClient:
    def __init__(self, endpoint: str, timeout_seconds: float) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def send_detection(self, payload: dict[str, Any]) -> None:
        if not self.endpoint:
            return

        base_url = self.endpoint
        # FastAPI con redirect_slashes=False puede responder 404 si falta/sobra '/'.
        # Intentamos primero con slash final para este backend.
        if base_url.endswith("/"):
            urls_to_try = [base_url, base_url.rstrip("/")]
        else:
            urls_to_try = [f"{base_url}/", base_url]

        for url in urls_to_try:
            try:
                response = httpx.post(url, json=payload, timeout=self.timeout_seconds)
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                return
            except httpx.HTTPStatusError:
                logger.exception("No se pudo enviar la deteccion al backend")
                return
            except Exception:
                logger.exception("No se pudo enviar la deteccion al backend")
                return

        logger.error(
            "Endpoint no encontrado (404). Revisa BACKEND_ENDPOINT: %s",
            self.endpoint,
        )
