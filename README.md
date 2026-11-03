# VISION

**VISION** is a local-first multi-agent command center inspired by the modular intelligence of fictional assistants such as JARVIS and FRIDAY. The name is intentional: VISION is the coordinator, while specialist agents handle focused work.

The first release is deliberately dependency-light so it can launch on Windows without Docker or a cloud account. It includes:

- A local web dashboard and API.
- A coordinator that routes work to specialist agents.
- Parallel execution for independent subtasks.
- Persistent SQLite task history, events, and memories.
- Explicit risk classification and approval gates.
- Optional Ollama-compatible model support.
- A Windows launcher that starts the service and opens the dashboard.

## Quick start

```powershell
cd D:\Unnamed
python -m vision
```

Or double-click `run_vision.bat`.

Open <http://127.0.0.1:8765> if the browser does not open automatically.

## Optional local model

VISION works in deterministic demo mode without a model. For richer responses, run Ollama and set:

```powershell
$env:VISION_LLM_PROVIDER = "ollama"
$env:VISION_OLLAMA_MODEL = "qwen3:8b"
python -m vision
```

The model is used only for synthesis; routing, permissions, persistence, and tool execution remain controlled by the runtime.

## Agent roster

| Agent | Responsibility |
|---|---|
| Vision Core | Coordinates tasks and presents results |
| Planner | Breaks complex requests into executable subtasks |
| Research | Research planning and source-oriented analysis |
| Coding | Repository inspection and implementation planning |
| System | Safe read-only Windows/system diagnostics |
| Memory | Persistent notes and recall |
| Security | Risk classification and approval policy |

## API

- `GET /api/health`
- `GET /api/agents`
- `GET /api/tasks`
- `POST /api/tasks` with `{ "prompt": "..." }`
- `POST /api/tasks/{id}/approve`
- `POST /api/tasks/{id}/cancel`
- `GET /api/events?after=<sequence>`
- `GET /api/memories?q=<query>`
- `POST /api/memories` with `{ "content": "...", "kind": "fact" }`

## Development

```powershell
python -m unittest discover -s tests -v
python -m vision --check
```

## Roadmap

The runtime is designed for incremental upgrades: MCP connectors, browser automation, voice, richer local models, sandboxed coding workspaces, scheduled routines, and a native desktop shell can be added without changing the coordinator contract.

VISION is an independent project and is not affiliated with Marvel, Disney, or any related rights holder.
