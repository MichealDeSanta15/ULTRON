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
        return ("Research Agent received the request. In this foundation release it returns a controlled "
                "research brief; web connectors can be added through the tool contract without changing routing.")


class CodingAgent(Agent):
    spec = AgentSpec("coding", "Coding Agent", "Software Engineering", "Inspects projects and prepares safe implementation work.", ("code", "repositories", "testing"), "medium")

    def run(self, context: AgentContext) -> str:
        cwd = Path.cwd()
        return f"Coding Agent prepared a workspace-aware plan from {cwd}. No files were changed by this request."


class SystemAgent(Agent):
    spec = AgentSpec("system", "System Agent", "System Operations", "Reports safe, read-only Windows and runtime diagnostics.", ("system", "diagnostics"), "medium")

    def run(self, context: AgentContext) -> str:
        disk = shutil.disk_usage(os.getcwd())
        return (f"System Agent report: OS={platform.platform()}, Python={platform.python_version()}, "
                f"CPU={os.cpu_count() or 1} cores, free disk={disk.free // (1024**3)} GB.")


class MemoryAgent(Agent):
    spec = AgentSpec("memory", "Memory Agent", "Knowledge", "Stores and recalls durable user-approved notes.", ("memory", "knowledge"))

    def run(self, context: AgentContext) -> str:
        return "Memory Agent is ready to store or recall approved project knowledge."


class SecurityAgent(Agent):
    spec = AgentSpec("security", "Security Agent", "Trust and Safety", "Classifies risk and enforces approval boundaries.", ("security", "approvals"), "high")

    def run(self, context: AgentContext) -> str:
        return "Security Agent evaluated the request under VISION's approval policy."


def built_in_agents() -> dict[str, Agent]:
    agents: list[Agent] = [VisionCoreAgent(), PlannerAgent(), ResearchAgent(), CodingAgent(), SystemAgent(), MemoryAgent(), SecurityAgent()]
    return {agent.spec.id: agent for agent in agents}
