#!/usr/bin/env python3
"""FastMCP‐aware HTTP transport adapter.

This adapter extends the existing ``HttpTransportAdapter`` so it can talk to
FastMCP servers that require:

* an SSE connection on ``/notifications`` (must be established first)
* a session-id sent both as query param and ``Mcp-Session-Id`` header
* 202 Accepted for each POST, with the real JSON-RPC response arriving on the
  SSE stream.

The public API (``start()``, ``stop()``, ``send_request()``, ``send_notification()``)
matches ``HttpTransportAdapter`` so the protocol adapters and compliance runner
can use it transparently.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional, Tuple, List

import requests
import sseclient

from .http import HttpTransportAdapter  # relative import within package


class FastMCPHttpAdapter(HttpTransportAdapter):
    """HTTP transport that understands the FastMCP SSE/202 pattern."""

    def __init__(self, *args: Any, **kwargs: Any):
        # Force debug flag into logger if requested
        self._debug = kwargs.get("debug", False)
        super().__init__(*args, **kwargs)

        # Override / extend some internals
        self._sse_connected = False
        self._sse_thread: Optional[threading.Thread] = None
        self._stop_sse = False
        self._sse_responses: Dict[str, Dict[str, Any]] = {}
        self._sse_response_event = threading.Event()
        self.logger = logging.getLogger("FastMCPHttpAdapter")
        if self._debug:
            self.logger.setLevel(logging.DEBUG)

    # ---------------------------------------------------------------------
    # SSE helpers
    # ---------------------------------------------------------------------
    def _sse_reader_thread(self):
        """Background thread that consumes SSE events and stores responses."""
        sse_url = f"{self.server_url}/notifications?session_id={self.session_id}"
        self.logger.debug(f"[SSE] connecting to {sse_url}")

        # Use a dedicated Session for the stream – requests.Session is not
        # thread-safe when shared.
        sse_session = requests.Session()
        headers = {
            "Accept": "text/event-stream",
            "Mcp-Session-Id": self.session_id,
            "Cache-Control": "no-cache",
        }
        try:
            response = sse_session.get(sse_url, stream=True, headers=headers, timeout=None)
            if response.status_code != 200:
                self.logger.error(f"SSE connection failed: {response.status_code}")
                return
            self._sse_connected = True
            self.logger.debug("[SSE] connection established")

            client = sseclient.SSEClient(response)
            for event in client.events():
                if self._stop_sse:
                    break
                data = event.data or ""
                if not data:
                    continue

                # Session ID update event (FastMCP sends the POST endpoint as
                # the very first event; extract session_id from it)
                if "session_id=" in data and not data.startswith("{"):
                    import re
                    m = re.search(r"session_id=([a-f0-9]+)", data)
                    if m:
                        self.session_id = m.group(1)
                        # Update headers for future POSTs
                        self.headers["Mcp-Session-Id"] = self.session_id
                        self.logger.debug(f"[SSE] updated session_id -> {self.session_id}")
                    continue

                # Otherwise expect JSON-RPC responses
                if data.startswith("{") and "\"jsonrpc\"" in data:
                    try:
                        msg = json.loads(data)
                        if "id" in msg:
                            self._sse_responses[msg["id"]] = msg
                            self._sse_response_event.set()
                            self.logger.debug(f"[SSE] stored response for id {msg['id']}")
                    except json.JSONDecodeError:
                        self.logger.debug(f"[SSE] non-JSON payload: {data[:80]}")
                        continue
        except Exception as exc:
            self.logger.error(f"SSE reader error: {exc}")
        finally:
            self._sse_connected = False
            self.logger.debug("[SSE] thread exiting")

    def _start_sse(self, timeout: float = 5.0) -> bool:
        """Ensure SSE thread is running and connected."""
        if self._sse_thread and self._sse_thread.is_alive():
            return self._sse_connected
        self._stop_sse = False
        self._sse_thread = threading.Thread(target=self._sse_reader_thread, daemon=True)
        self._sse_thread.start()
        start = time.time()
        while time.time() - start < timeout:
            if self._sse_connected:
                return True
            time.sleep(0.1)
        self.logger.warning("Timed out waiting for SSE connection")
        return False

    def _stop_sse_reader(self):
        self._stop_sse = True
        self._sse_response_event.set()
        if self._sse_thread and self._sse_thread.is_alive():
            try:
                self._sse_thread.join(timeout=2.0)
            except RuntimeError:
                pass
        self._sse_thread = None
        self._sse_connected = False

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def start(self) -> bool:  # noqa: D401
        """Connect to existing FastMCP server; no subprocess launch."""
        if self.is_started:
            return True
        if not self.server_url:
            raise ValueError("server_url must be supplied for FastMCP HTTP adapter")

        # Establish SSE first (creates/updates session_id)
        if not self._start_sse():
            return False

        self.is_started = True
        return True

    def stop(self):  # type: ignore[override]
        self.logger.debug("Stopping FastMCP HTTP adapter")
        self._stop_sse_reader()
        super().stop()

    # ---------------------------------------------------------------
    def _wait_for_sse_response(self, req_id: str, timeout: float) -> Tuple[bool, Optional[Dict[str, Any]]]:
        start = time.time()
        while time.time() - start < timeout:
            if req_id in self._sse_responses:
                return True, self._sse_responses.pop(req_id)
            self._sse_response_event.wait(0.1)
            self._sse_response_event.clear()
        return False, None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_started:
            raise RuntimeError("Transport not started")
        if not self._sse_connected:
            self._start_sse()

        request_id = request_id or str(uuid.uuid4())
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params is not None:
            req["params"] = params

        # Ensure URL has session param
        url = f"{self.server_url}?session_id={self.session_id}"
        self.logger.debug(f"POST {url} -> {method} id={request_id}")
        try:
            resp = self.session.post(url, json=req, headers=self.headers, timeout=self.timeout)
        except Exception as exc:
            raise RuntimeError(f"HTTP POST failed: {exc}") from exc

        # FastMCP returns 202 always
        if resp.status_code not in (202, 200):
            raise RuntimeError(f"Unexpected HTTP status {resp.status_code}: {resp.text[:120]}")

        ok, msg = self._wait_for_sse_response(request_id, self.timeout)
        if not ok:
            raise TimeoutError(f"Timed out waiting for response id {request_id}")
        return msg  # type: ignore[return-value]

    def send_notification(self, notification: Dict[str, Any]) -> None:
        # Notifications have no id and we don't expect a response; still need 202.
        url = f"{self.server_url}?session_id={self.session_id}"
        self.session.post(url, json=notification, headers=self.headers, timeout=self.timeout) 