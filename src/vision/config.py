from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Path("data")
    llm_provider: str = "deterministic"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"

    @classmethod
    def from_environment(cls, host: str | None = None, port: int | None = None) -> "Settings":
        root = Path(__file__).resolve().parents[2]
        data_dir = Path(os.getenv("VISION_DATA_DIR", str(root / "data")))
        return cls(
            host=host or os.getenv("VISION_HOST", "127.0.0.1"),
            port=port or int(os.getenv("VISION_PORT", "8765")),
            data_dir=data_dir,
            llm_provider=os.getenv("VISION_LLM_PROVIDER", "deterministic").lower(),
            ollama_base_url=os.getenv("VISION_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.getenv("VISION_OLLAMA_MODEL", "qwen3:8b"),
        )
