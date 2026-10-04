# `q_link` — Developer Instructions & Architecture Guide
## Automated Forensic Relationship & Intelligence Engine

---

### 1. Architectural Layout & Responsibilities
Conforms strictly to the **Agentic Django** design pattern:

```
apps/q_link/
├── backend/
│   ├── dispatcher.py    # Decoupled ingestion hook: emit_forensic_finding(...)
│   ├── llm_agent.py     # ForensicCopilotAgent & ForensicToolRegistry (Tool Calling)
│   └── sync_all.py      # Cross-module historical synthesizer (apps.get_model)
├── models.py            # ForensicEntity, EntityAlias, EntityRelationship, EvidencePointer, ForensicTimelineEvent, RelationshipAlert
├── selectors.py         # Read-only queries, BFS pathfinder, graph overview (N+1 eliminated)
├── services.py          # Atomic mutations, RapidFuzz entity resolution, risk rule evaluator
├── views.py             # Thin view controllers & JSON REST APIs
├── urls.py              # URL routing configuration
├── SCHEMA.md            # dbdiagram.io DBML specification
├── USER_GUIDE.md        # Investigator workstation workflow
└── INSTRUCTION.md       # Developer instructions & rules
```

---

### 2. Strict Rules for Interns & Developers
1. **Model Inheritance**: All models MUST inherit from `core.models.ForensicBaseModel` (`id` UUID v4, `created_at`, `updated_at`).
2. **Decoupled Ingestion**: Upstream forensic modules must NOT import Q-Link views. They emit events via `emit_forensic_finding` from `q_link.backend.dispatcher`.
3. **No Business Logic in Views**: Views must solely parse HTTP inputs, call `services.py` or `selectors.py`, and return JSON / rendered templates.
4. **Atomic Transactions**: All mutations in `services.py` must use `@transaction.atomic`.
5. **Cotton Template Standards**:
   * Use `<c-base>`, `<c-page_header>`, `<c-stat_card>`.
   * Never use illegal `<c-slot:name>` tags. Always use `<c-slot name="...">`.
6. **Tool-Calling Interface**: Any new investigative tool must be registered in `ForensicToolRegistry.get_tool_definitions()` with JSON schema validation.

---

### 3. Testing & Pre-Commit Verification
Run the validator script to ensure documentation, Cotton tag safety, and Django checks pass:
```bash
uv run python scripts/validate_project.py
uv run python manage.py test q_link
```
