from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import Settings


class LLMClient:
    """Optional synthesis client. The runtime remains usable without an LLM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, prompt: str, specialist_results: list[str]) -> str:
        if self.settings.llm_provider != "ollama":
            return self._deterministic(prompt, specialist_results)
        body = json.dumps({
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [{
                "role": "system",
                "content": "You are VISION, a concise multi-agent coordinator. Summarize verified specialist results. Do not claim actions that are not in the results.",
            }, {"role": "user", "content": f"Request: {prompt}\n\nSpecialist results:\n" + "\n".join(specialist_results)}],
        }).encode()
        request = urllib.request.Request(
            f"{self.settings.ollama_base_url}/api/chat", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode())
            return data.get("message", {}).get("content") or self._deterministic(prompt, specialist_results)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return self._deterministic(prompt, specialist_results) + " (Ollama unavailable; deterministic fallback used.)"

    @staticmethod
    def _deterministic(prompt: str, specialist_results: list[str]) -> str:
        if not specialist_results:
            return f"VISION received: {prompt}"
        return "VISION completed the request with these verified specialist results:\n" + "\n".join(
            f"• {result}" for result in specialist_results
        )
