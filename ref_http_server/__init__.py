"""Reference MCP HTTP/SSE server package.

Usage
-----
    python -m ref_http_server --port 8085 --debug

This module simply forwards to ``ref_http_server.fastmcp_server`` which hosts a
FastMCP-powered HTTP + SSE reference implementation suitable for the
``mcp_testing/scripts/http_compliance.py`` test harness.
"""

from __future__ import annotations

import asyncio
from importlib import import_module
from types import ModuleType
from typing import Any


# Lazily import the actual server script so we don't pull heavy deps (uvicorn,
# mcp, etc.) when someone merely *imports* the package.
def _load_server() -> ModuleType:
    return import_module("ref_http_server.fastmcp_server")


def main(*args: Any, **kwargs: Any) -> None:  # noqa: D401
    """Entry-point wrapper that delegates to ``fastmcp_server.main``.

    This lets you start the server with ``python -m ref_http_server`` or via a
    console-script entry-point that calls ``ref_http_server:main``.
    """

    server_mod = _load_server()

    # The actual ``main`` in fastmcp_server is **async**.  We detect that and
    # run it properly under ``asyncio``.
    import inspect
    if inspect.iscoroutinefunction(server_mod.main):
        asyncio.run(server_mod.main(*args, **kwargs))
    else:
        server_mod.main(*args, **kwargs) 