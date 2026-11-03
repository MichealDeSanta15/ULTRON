from __future__ import annotations

import os
import platform
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    description: str
    agents: tuple[str, ...]
    risk_level: str = "low"


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    handler: Callable[..., dict[str, Any]]


class ToolRegistry:
    """A small, explicit capability registry used by specialist agents."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self.register(ToolSpec("system_snapshot", "System Snapshot", "Read-only runtime and disk diagnostics.", ("system",)))
        self.register(ToolSpec("workspace_snapshot", "Workspace Snapshot", "Read-only view of the current workspace.", ("coding",)))
        self.register(ToolSpec("fetch_url", "Fetch URL", "Fetch a user-requested URL for research analysis.", ("research",), "medium"))

    def register(self, spec: ToolSpec, handler: Callable[..., dict[str, Any]] | None = None) -> None:
        self._tools[spec.id] = Tool(spec, handler or self._default_handler(spec.id))

    def specs(self) -> list[dict[str, Any]]:
        return [vars(tool.spec) for tool in self._tools.values()]

    def execute(self, tool_id: str, **arguments: Any) -> dict[str, Any]:
        tool = self._tools.get(tool_id)
        if not tool:
            raise KeyError(f"unknown tool: {tool_id}")
        return tool.handler(**arguments)

    @staticmethod
    def _default_handler(tool_id: str) -> Callable[..., dict[str, Any]]:
        if tool_id == "system_snapshot":
            def system_snapshot() -> dict[str, Any]:
                disk = shutil.disk_usage(os.getcwd())
                return {"os": platform.platform(), "python": platform.python_version(),
                        "cpu_count": os.cpu_count() or 1, "free_disk_gb": disk.free // (1024**3)}
            return system_snapshot
        if tool_id == "workspace_snapshot":
            def workspace_snapshot() -> dict[str, Any]:
                root = Path.cwd()
                entries = sorted(item.name for item in root.iterdir())[:40]
                return {"workspace": str(root), "entries": entries, "entry_count": len(entries)}
            return workspace_snapshot
        if tool_id == "fetch_url":
            def fetch_url(url: str) -> dict[str, Any]:
                request = urllib.request.Request(url, headers={"User-Agent": "VISION/0.1"})
                with urllib.request.urlopen(request, timeout=8) as response:
                    body = response.read(12000).decode("utf-8", errors="replace")
                    return {"url": url, "content_type": response.headers.get("content-type", ""),
                            "status": response.status, "body": body, "characters": len(body)}
            return fetch_url
        def unavailable(**_: Any) -> dict[str, Any]:
            raise RuntimeError(f"tool {tool_id} has no handler")
        return unavailable
