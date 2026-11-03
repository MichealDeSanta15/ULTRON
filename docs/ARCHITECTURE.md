# VISION architecture

VISION uses a **controlled coordinator + specialist agents** model. Every request passes through the runtime, so no individual agent owns the whole machine or the whole conversation.

```text
User / dashboard / future voice clients
                 |
          HTTP API + event log
                 |
            VISION runtime
        /       |        \
   route     risk gate     memory
      |         |           |
  specialist  approval   SQLite
      |
  parallel task executor
      |
  verified results -> optional model synthesis -> dashboard
```

## Agent contract

Each agent exposes an `AgentSpec` and a `run(AgentContext)` method. `AgentSpec` is the future plugin boundary: an external MCP adapter, browser agent, voice agent, or native desktop agent can register the same metadata without changing the dashboard or task lifecycle.

Agents receive capabilities through `ToolRegistry`. Every tool has an ID, description, owning agents, risk level, and handler. The registry is exposed at `GET /api/tools`, which makes the active capability surface inspectable before integrations are added.

An agent should:

1. Have one clear responsibility.
2. Receive a bounded context and explicit tools.
3. Return a human-readable result or a structured result in a later API version.
4. Never silently perform high-impact side effects.
5. Emit enough information for the coordinator to verify what happened.

## Routing and parallelism

The current router uses deterministic keyword classification first. Complex prompts can activate the planner plus several independent specialists. Specialists execute in parallel on a separate worker pool, while task lifecycle work uses its own pool to avoid nested-executor deadlocks.

This is intentional: predictable routing handles safety-critical boundaries, while optional LLM synthesis improves natural-language quality after the facts are collected.

## Safety model

- The service binds to `127.0.0.1` by default.
- Destructive, credential, payment, shutdown, deletion, and outbound-message language is marked high risk.
- High-risk tasks enter `awaiting_approval` and do not execute until approved.
- The current coding and system agents are read-only/planning-oriented.
- Web content is treated as data; it is not granted authority to change routing or permissions.
- Every task and event is persisted in SQLite before the dashboard displays it.

## Extension path

The next integration layers should preserve this boundary:

- MCP client adapters for external tools.
- A browser agent with a Playwright workspace.
- A coding agent with an isolated project workspace and test verifier.
- Voice transport using wake word, STT, and TTS.
- Scheduled tasks and background notifications.
- Native desktop shell wrapping the local dashboard.
