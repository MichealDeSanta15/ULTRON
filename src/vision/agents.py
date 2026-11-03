from __future__ import annotations

import os
import platform
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import AgentSpec


@dataclass
class AgentContext:
    task_id: str
    prompt: str
    metadata: dict[str, Any]


class Agent(ABC):
    spec: AgentSpec

    @abstractmethod
    def run(self, context: AgentContext) -> str:
        raise NotImplementedError


class VisionCoreAgent(Agent):
    spec = AgentSpec("vision-core", "Vision Core", "Coordinator", "Coordinates specialist agents and synthesizes results.", ("coordination", "synthesis"))

    def run(self, context: AgentContext) -> str:
        return f"VISION coordinated the request: {context.prompt}"


class PlannerAgent(Agent):
    spec = AgentSpec("planner", "Planner", "Task Decomposition", "Breaks a request into focused, inspectable subtasks.", ("planning", "routing"))

    def run(self, context: AgentContext) -> str:
        return "The planner prepared specialist work for this request."


class ResearchAgent(Agent):
    spec = AgentSpec("research", "Research Agent", "Research", "Creates source-oriented research plans and summaries.", ("research", "analysis"))

    def run(self, context: AgentContext) -> str:
        url = next((word.strip(".,!?()[]") for word in context.prompt.split() if word.startswith(("http://", "https://"))), None)
        if url:
            try:
                result = context.metadata["tools"].execute("fetch_url", url=url)
                content_type = result["content_type"]
                body = result["body"]
                title = ""
                if "<title" in body.lower():
                    title = body.lower().split("<title", 1)[1].split(">", 1)[-1].split("</title", 1)[0].strip()
                return f"Research Agent fetched {url} ({content_type}); title={title or 'unavailable'}; received {len(body)} characters for analysis."
            except (TimeoutError, OSError, RuntimeError) as exc:
                return f"Research Agent could not fetch {url}: {exc}"
        return ("Research Agent received the request. In this foundation release it returns a controlled "
                "research brief; web connectors can be added through the tool contract without changing routing.")


class CodingAgent(Agent):
    spec = AgentSpec("coding", "Coding Agent", "Software Engineering", "Inspects projects and prepares safe implementation work.", ("code", "repositories", "testing"), "medium")

    def run(self, context: AgentContext) -> str:
        snapshot = context.metadata["tools"].execute("workspace_snapshot")
        return f"Coding Agent prepared a workspace-aware plan from {snapshot['workspace']} ({snapshot['entry_count']} visible entries). No files were changed by this request."


class SystemAgent(Agent):
    spec = AgentSpec("system", "System Agent", "System Operations", "Reports safe, read-only Windows and runtime diagnostics.", ("system", "diagnostics"), "medium")

    def run(self, context: AgentContext) -> str:
        snapshot = context.metadata["tools"].execute("system_snapshot")
        return (f"System Agent report: OS={snapshot['os']}, Python={snapshot['python']}, "
                f"CPU={snapshot['cpu_count']} cores, free disk={snapshot['free_disk_gb']} GB.")


class MemoryAgent(Agent):
    spec = AgentSpec("memory", "Memory Agent", "Knowledge", "Stores and recalls durable user-approved notes.", ("memory", "knowledge"))

    def run(self, context: AgentContext) -> str:
        store = context.metadata.get("store")
        if store is not None:
            text = context.prompt.strip()
            lowered = text.lower()
            if lowered.startswith(("remember ", "note ", "save ")):
                content = text.split(" ", 1)[1].strip()
                memory = store.add_memory("user_note", content)
                return f"Memory Agent saved note #{memory['id']}: {content}"
            query = text
            for prefix in ("recall ", "what do you remember about ", "search memory "):
                if lowered.startswith(prefix):
                    query = text[len(prefix):].strip()
                    break
            memories = store.search_memories(query)
            if memories:
                return "Memory Agent recalled:\n" + "\n".join(f"• {item['content']}" for item in memories)
            return "Memory Agent found no matching durable notes."
        return "Memory Agent is ready to store or recall approved project knowledge."


class SecurityAgent(Agent):
    spec = AgentSpec("security", "Security Agent", "Trust and Safety", "Classifies risk and enforces approval boundaries.", ("security", "approvals"), "high")

    def run(self, context: AgentContext) -> str:
        return "Security Agent evaluated the request under VISION's approval policy."


def built_in_agents() -> dict[str, Agent]:
    agents: list[Agent] = [VisionCoreAgent(), PlannerAgent(), ResearchAgent(), CodingAgent(), SystemAgent(), MemoryAgent(), SecurityAgent()]
    return {agent.spec.id: agent for agent in agents}
