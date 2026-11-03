from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .runtime import VisionRuntime
from .ui import DASHBOARD_HTML


class VisionHTTPServer(ThreadingHTTPServer):
    def __init__(self, address, handler, runtime: VisionRuntime):
        self.runtime = runtime
        super().__init__(address, handler)


class VisionRequestHandler(BaseHTTPRequestHandler):
    server: VisionHTTPServer

    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, status: int, payload, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else (payload.encode() if isinstance(payload, str) else json.dumps(payload).encode())
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        return json.loads(raw or b"{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        runtime = self.server.runtime
        try:
            if path in {"/", "/index.html"}:
                self._send(HTTPStatus.OK, DASHBOARD_HTML, "text/html")
            elif path == "/api/health":
                self._send(HTTPStatus.OK, runtime.health())
            elif path == "/api/overview":
                self._send(HTTPStatus.OK, runtime.overview())
            elif path == "/api/agents":
                self._send(HTTPStatus.OK, {"agents": runtime.agent_specs()})
            elif path == "/api/tasks":
                self._send(HTTPStatus.OK, {"tasks": runtime.store.list_tasks()})
            elif path.startswith("/api/tasks/"):
                task_id = path.split("/")[3]
                task = runtime.store.get_task(task_id)
                self._send(HTTPStatus.OK, {"task": task} if task else {"error": "task not found"})
            elif path == "/api/events":
                after = int(query.get("after", [0])[0])
                self._send(HTTPStatus.OK, {"events": runtime.store.events(after=after)})
            elif path == "/api/memories":
                self._send(HTTPStatus.OK, {"memories": runtime.store.search_memories(query.get("q", [""])[0])})
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except (ValueError, TypeError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:
        runtime = self.server.runtime
        try:
            body = self._json_body()
            if self.path == "/api/tasks":
                task = runtime.create_task(str(body.get("prompt", "")))
                self._send(HTTPStatus.ACCEPTED, {"task": runtime.store.get_task(task.id)})
            elif self.path.startswith("/api/tasks/") and self.path.endswith("/approve"):
                task_id = self.path.split("/")[3]
                self._send(HTTPStatus.OK, {"task": runtime.approve_task(task_id)})
            elif self.path.startswith("/api/tasks/") and self.path.endswith("/cancel"):
                task_id = self.path.split("/")[3]
                self._send(HTTPStatus.OK, {"task": runtime.cancel_task(task_id)})
            elif self.path == "/api/memories":
                content = str(body.get("content", "")).strip()
                if not content:
                    raise ValueError("content is required")
                memory = runtime.store.add_memory(str(body.get("kind", "note")), content)
                runtime.log_event("memory", "Memory saved", memory)
                self._send(HTTPStatus.CREATED, {"memory": memory})
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except ValueError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
