"""Client for Hermes to talk to the Hermes-Claude Bridge server."""

from __future__ import annotations

from typing import Any

import httpx


class BridgeClient:
    """Async client for the bridge HTTP/SSE API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._http = http_client or httpx.AsyncClient(base_url=self.base_url, timeout=60)

    async def health(self) -> dict[str, Any]:
        """Check server health."""
        resp = await self._http.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def create_session(
        self,
        working_dir: str,
        model: str | None = None,
        permissions_mode: str = "acceptEdits",
    ) -> dict[str, Any]:
        """Create a new Claude session on the bridge server."""
        resp = await self._http.post(
            "/sessions",
            json={
                "working_dir": working_dir,
                "model": model,
                "permissions_mode": permissions_mode,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session metadata."""
        resp = await self._http.get(f"/sessions/{session_id}")
        resp.raise_for_status()
        return resp.json()

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        context_files: list[str] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Send a prompt to a session and return Claude's result."""
        resp = await self._http.post(
            f"/sessions/{session_id}/prompt",
            json={
                "prompt": prompt,
                "context_files": context_files or [],
                "timeout": timeout,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def answer_question(self, session_id: str, answer: str) -> dict[str, Any]:
        """Answer a question Claude asked in a session."""
        resp = await self._http.post(
            f"/sessions/{session_id}/answer",
            json={"answer": answer},
        )
        resp.raise_for_status()
        return resp.json()

    async def stream_events(self, session_id: str):
        """Stream SSE events from a session (async generator).

        Requires an external SSE parser such as `sseclient-py` or `aiohttp-sse-client`.
        For simplicity, this method yields raw EventSource lines.
        """
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET", f"{self.base_url}/sessions/{session_id}/events"
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield {"data": line[6:]}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
