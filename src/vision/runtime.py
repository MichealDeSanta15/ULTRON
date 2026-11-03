from __future__ import annotations

import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .agents import AgentContext, built_in_agents
from .config import Settings
from .llm import LLMClient
from .models import Task
from .store import Store


class VisionRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = Store(settings.data_dir)
        self.agents = built_in_agents()
        self.llm = LLMClient(settings)
        self._task_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="vision-task")
        self._agent_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="vision-agent")
        self._lock = threading.RLock()

    def health(self) -> dict[str, Any]:
        return {"name": "VISION", "version": "0.1.0", "status": "online", "agents": len(self.agents),
                "llm_provider": self.settings.llm_provider, "data_dir": str(self.settings.data_dir)}

    def agent_specs(self) -> list[dict[str, Any]]:
        return [vars(agent.spec) for agent in self.agents.values()]

    def overview(self) -> dict[str, Any]:
        tasks = self.store.list_tasks(limit=200)
        counts = Counter(task["status"] for task in tasks)
        events = self.store.events(limit=10000)
        return {
            "health": self.health(),
            "task_counts": dict(counts),
            "active_tasks": sum(counts.get(status, 0) for status in ("queued", "running", "awaiting_approval")),
            "completed_tasks": counts.get("completed", 0),
            "event_count": events[-1]["sequence"] if events else 0,
        }

    def log_event(self, kind: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.store.event(kind, message, payload)

    def create_task(self, prompt: str) -> Task:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("prompt is required")
        task = Task(prompt=prompt)
        task.route, task.risk = self._route(prompt)
        self.store.save_task(task)
        self.log_event("task", "Task queued", {"task_id": task.id, "route": task.route, "risk": task.risk})
        if task.risk == "high":
            task.status = "awaiting_approval"
            task.touch()
            self.store.save_task(task)
            self.log_event("security", "Approval required before execution", {"task_id": task.id})
        else:
            self._task_executor.submit(self._execute, task.id)
        return task

    def approve_task(self, task_id: str) -> dict[str, Any] | None:
        task = self.store.get_task(task_id)
        if not task or task["status"] != "awaiting_approval":
            return task
        task_obj = Task(prompt=task["prompt"], id=task["id"], status="queued", route=task["route"], risk=task["risk"],
                        result=task["result"], error=task["error"], created_at=task["created_at"], updated_at=task["updated_at"], subtasks=task["subtasks"])
        self.store.save_task(task_obj)
        self.log_event("security", "Task approved", {"task_id": task_id})
        self._task_executor.submit(self._execute, task_id)
        return self.store.get_task(task_id)

    def cancel_task(self, task_id: str) -> dict[str, Any] | None:
        task = self.store.get_task(task_id)
        if not task:
            return None
        task_obj = Task(prompt=task["prompt"], id=task["id"], status="cancelled", route=task["route"], risk=task["risk"],
                        result=task["result"], error=task["error"], created_at=task["created_at"], updated_at=task["updated_at"], subtasks=task["subtasks"])
        self.store.save_task(task_obj)
        self.log_event("task", "Task cancelled", {"task_id": task_id})
        return self.store.get_task(task_id)

    def _execute(self, task_id: str) -> None:
        raw = self.store.get_task(task_id)
        if not raw or raw["status"] in {"cancelled", "awaiting_approval"}:
            return
        task = Task(prompt=raw["prompt"], id=raw["id"], status="running", route=raw["route"], risk=raw["risk"],
                    result=raw["result"], error=raw["error"], created_at=raw["created_at"], updated_at=raw["updated_at"], subtasks=raw["subtasks"])
        self.store.save_task(task)
        self.log_event("task", "Task started", {"task_id": task.id})
        try:
            routes = self._subtask_routes(task.prompt, task.route)
            futures = {}
            for route in routes:
                agent = self.agents[route]
                self.log_event("agent", f"{agent.spec.name} started", {"task_id": task.id, "agent": route})
                futures[self._agent_executor.submit(agent.run, AgentContext(task.id, task.prompt, {"store": self.store}))] = route
            results: list[str] = []
            for future in as_completed(futures):
                route = futures[future]
                result = future.result()
                results.append(result)
                task.subtasks.append({"agent": route, "status": "completed", "result": result})
                self.log_event("agent", f"{self.agents[route].spec.name} completed", {"task_id": task.id, "agent": route})
            task.result = self.llm.synthesize(task.prompt, results)
            task.status = "completed"
            self.log_event("task", "Task completed", {"task_id": task.id})
        except Exception as exc:  # keep task lifecycle terminal and inspectable
            task.status = "failed"
            task.error = str(exc)
            self.log_event("error", "Task failed", {"task_id": task.id, "error": str(exc)})
        task.touch()
        self.store.save_task(task)

    @staticmethod
    def _route(prompt: str) -> tuple[str, str]:
        text = prompt.lower()
        matches = lambda words: any((word in text if " " in word or "://" in word else re.search(rf"\b{re.escape(word)}\b", text)) for word in words)
        risk = "high" if re.search(r"\b(delete|remove|shutdown|restart|send|purchase|pay|password|credential)\b", text) else "low"
        if matches(("code", "bug", "repository", "repo", "build", "test", "implement")):
            return "coding", risk
        if matches(("research", "compare", "latest", "sources", "find out", "investigate")):
            return "research", risk
        if matches(("cpu", "memory", "disk", "system", "process", "windows", "computer")):
            return "system", risk
        if matches(("remember", "recall", "memory", "note")):
            return "memory", risk
        return "vision-core", risk

    @staticmethod
    def _subtask_routes(prompt: str, primary: str) -> list[str]:
        text = prompt.lower()
        routes = [primary]
        keyword_routes = (
            ("coding", ("code", "bug", "repository", "repo", "build", "test", "implement")),
            ("research", ("research", "compare", "latest", "sources", "find out", "investigate", "http://", "https://")),
            ("system", ("cpu", "memory", "disk", "system", "process", "windows", "computer")),
            ("memory", ("remember", "recall", "memory", "note")),
        )
        for route, keywords in keyword_routes:
            if route != primary and any((word in text if " " in word or "://" in word else re.search(rf"\b{re.escape(word)}\b", text)) for word in keywords):
                routes.append(route)
        if primary != "planner" and len(text.split()) >= 10:
            routes.insert(0, "planner")
        return routes

    def close(self) -> None:
        self._task_executor.shutdown(wait=False, cancel_futures=True)
        self._agent_executor.shutdown(wait=False, cancel_futures=True)
        self.store.close()
