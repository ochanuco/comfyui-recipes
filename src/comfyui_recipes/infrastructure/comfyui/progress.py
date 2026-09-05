"""ComfyUI's own broadcast socket, read for sampling progress only.

ComfyUI's /prompt accepts no client_id from this client, so it broadcasts
`progress` events to every connected /ws client -- this feed rides that
broadcast rather than opening a second, scoped connection.
"""

from __future__ import annotations

import json

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

from ..ws import WebSocketClosed, websocket_url


class FeedClosed(WebSocketClosed):
    """The ComfyUI progress socket is closed or broken."""


class ProgressFeed:
    """Connects to ComfyUI's `/ws` and yields `progress` events only."""

    def __init__(self, base_url: str) -> None:
        self.url = websocket_url(base_url, "/ws")
        self._socket = None

    def open(self) -> "ProgressFeed":
        try:
            self._socket = connect(self.url, open_timeout=20, extensions=[])
        except WebSocketException as error:
            raise FeedClosed(str(error)) from error
        return self

    def recv(self, timeout: float) -> dict | None:
        try:
            raw = self._socket.recv(timeout=timeout)
        except TimeoutError:
            return None
        except WebSocketException as error:
            raise FeedClosed(str(error)) from error
        try:
            message = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(message, dict) or message.get("type") != "progress":
            return None
        data = message.get("data") or {}
        return {"step": data.get("value"), "total": data.get("max"),
                "prompt_id": data.get("prompt_id")}

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except WebSocketException:
                pass
