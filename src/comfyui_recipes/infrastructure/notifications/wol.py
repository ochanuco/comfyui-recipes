"""Tells the Wake-on-LAN service that this host is about to sleep."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from ..chimera.client import USER_AGENT


class WolNotifier:
    def __init__(self, repository: Path, *, timeout: float = 3) -> None:
        self.target_file = repository / ".local/wol-notify"
        self.timeout = timeout

    def _target(self) -> tuple[str, str]:
        url = os.environ.get("WOL_NOTIFY_URL", "").strip()
        token = os.environ.get("WOL_NOTIFY_TOKEN", "").strip()
        if not (url and token) and self.target_file.exists():
            lines = self.target_file.read_text(encoding="utf-8").splitlines()
            url = url or (lines[0].strip() if lines else "")
            token = token or (lines[1].strip() if len(lines) > 1 else "")
        if not (url and token):
            raise SystemExit(
                "no wol target: set $WOL_NOTIFY_URL and $WOL_NOTIFY_TOKEN or write "
                f"the URL and the token on two lines of {self.target_file}")
        return url, token

    def announce(self, reason: str) -> None:
        url, token = self._target()
        request = urllib.request.Request(
            url, data=json.dumps({"reason": reason}).encode(), method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            })
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            if response.status != 204:
                raise SystemExit(f"wol answered HTTP {response.status}")
