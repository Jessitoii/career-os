# Career OS Architecture Overview

## Modular Layout
The system is divided into decoupled microservices communicating via Redis queues and HTTP APIs.

```text
├── app/
│   ├── api/            # FastAPI Endpoints and WebSockets
│   ├── automation/     # Playwright ATS Adapters & Stealth logic
│   ├── core/           # DB, Settings, and State Machine logic
│   ├── intelligence/   # LLM integration (Groq, Cerebras) & Scoring
│   ├── hitl/           # Telegram Bot polling
│   └── models/         # SQLAlchemy ORM schemas
├── frontend/           # Next.js GUI
├── tests/              # Pytest verification
└── docs/               # Technical references
```

## The State Machine Core
All job applications are managed by `app.core.state_machine`, enforcing strict forward-only transitions to prevent runaway agent actions:

`scraped` -> `scored` -> `pending_approval` -> `approved` -> `applying` -> `applied`

The **HitL (Human in the Loop)** system bridges `pending_approval` -> `approved`. This is orchestrated simultaneously via:
1. **Telegram:** Inline Keyboards prompting "Approve" or "Reject".
2. **Web GUI:** The Kanban dashboard.

## Provider Constraints
The `intelligence` module (`llm_client.py`) strictly isolates requests to **Groq** and **Cerebras**. It explicitly avoids Anthropic models or SDKs. The module `scoring.py` uses an Ollama proxy container (`nomic-embed-text`) to filter irrelevant matches via semantic cosine similarity before querying the remote LLMs, drastically reducing API token burn.
