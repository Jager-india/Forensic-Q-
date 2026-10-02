# Django Architecture & Code Style Rules

## 1. Domain Separation (4-Tier Architecture)
- **`backend/`**: Dedicated forensic analysis scripts, parsers, classifiers, and algorithmic calculations. Kept independent from Django web request lifecycles.
- **`models.py`**: Clean declarative models inheriting from `core.models.ForensicBaseModel`. Implement `__str__()` on all models. No complex business logic in `save()`.
- **`selectors.py`**: All read-only database queries. Always eliminate N+1 queries with `select_related()` and `prefetch_related()`. No database writes in selectors.
- **`services.py`**: All business workflows, file ingestion orchestration, and mutations calling `backend/`. Decorate multi-model writes with `@transaction.atomic`.
- **`views.py`**: Thin controllers. Only parse HTTP requests, invoke selectors/services, and render Cotton templates or JSON.

## 2. Django Cotton Template Guidelines
- Always use `<c-slot name="actions">` instead of `<c-slot:actions>` to ensure Windows compatibility (`WinError 123`).
- Keep components modular and leverage design system tokens defined in `ui/`.

## 3. Database & Migrations
- Model schemas must match the DBML specifications in each app's `SCHEMA.md` ([dbdiagram.io](https://dbdiagram.io)).
- Never commit model changes without generating migration files (`uv run python manage.py makemigrations`).

## 4. Logging Standards (Loguru)
- Always use `from loguru import logger` instead of standard `logging.getLogger(__name__)`.
- Logging output is centralized in `core/logging.py` (colorized console + rotating file logs under `logs/`).
- Never swallow exceptions with bare `pass` or `continue` (Bandit `B110`, `B112`); always log them with `logger.debug(...)` or `logger.warning(...)`.

## 5. Large File Uploads & Forensic Ingestion (50+ GB)
- Massive evidence files (PSTs, disk images, PCAPs, bank databases) must use `core.file_uploader.FileUploader` for resumable binary chunking to disk.
- Compute SHA-256 evidence chain of custody hashes automatically during streaming.
- Process large files in background threads with progress callbacks, flushing database records in batches of 250 via `bulk_create()` wrapped in `@transaction.atomic`.

## 6. Uniform Q-App File & UI Terminology Standards (NO Backward Compatibility Shims)
- **Primary View Controller**: Always name the main dashboard view `def dashboard_view(request: HttpRequest) -> HttpResponse:`. Never create or retain legacy alias variables (e.g. `bank_dashboard_view = dashboard_view`).
- **Primary URL Route**: Always route the dashboard as `path("", views.dashboard_view, name="dashboard")`. Never add redundant backward-compatible alias routes (e.g. `name="list"` or `name="landing"`).
- **Template Naming**:
  - Main hub template: Always `templates/<app_name>/dashboard.html`. Never retain legacy templates like `landing.html` with backward-compatible shims or `{% include %}` blocks.
  - Entity detail template: Always `templates/<app_name>/<entity>_detail.html` (e.g., `person_detail.html`, `investigation_detail.html`, `device_detail.html`, `case_detail.html`, `recording_detail.html`, `channel_detail.html`).
- **UI Terminology Standard Across All Q-Apps**:
  - **Header Action Button**: `Import <Data Artifact>` (e.g., `Import Bank Statement`, `Import PST Mailbox`, `Import Scan Findings`, `New Verification Case`, `Import Audio Recording`, `Import Chat Export`, `Import SAP Records`).
  - **Directory Section Heading**: `<Entities> Directory` (e.g., `Target Auditees Directory`, `Audited Mailboxes Directory`, `Audited Endpoints Directory`, `Verification Cases Directory`, `Voice Recordings Directory`, `Audited Chat Channels Directory`).
  - **Directory Live Search**: Standardized real-time Alpine.js filter with placeholder `Search <entities> directory...`, `xmark` clear button, and `<N> Item(s) Configured` badge.
  - **Investigation Profile Selector**: Always use `<c-profile_selector label="Target Auditee / Investigation Profile" name="profile_id" ... />` inside upload modals, resolved in backend via `core.profiles.resolve_or_create_profile_from_request`.
- **Strict Prohibition on Backward Compatibility**:
  - Do NOT create backward-compatible wrapper functions, duplicate URL names, or shim template files.
  - Directly migrate all callers, tests, and links to the unified standard.

