# ForensiQ — Developer Instructions & Architecture Guide

## 1. Project Overview & Vision

**ForensiQ** is a modern, high-performance forensic investigation and analytical workstation built on **Django 6.1**, **django-cotton**, **Tabulator.js**, and **Plotly.py**.

Key platform capabilities:
- **Instant Client-Side Interactivity:** Tabulator.js handles sorting, pagination, column reordering, multi-field filtering, and CSV/JSON export on the client side without unnecessary server roundtrips.
- **Centralized Violet Design System:** Curated `#502D55` dark-violet theme and `#f4ecf5` soft light-violet theme with Aptos typography, synchronous FOUC prevention, and synchronized dark/light toggle.
- **Component-Driven HTML-First Architecture:** Clean, modular Django Cotton custom tags (`<c-base>`, `<c-page_header>`, `<c-stat_card>`, `<c-card>`, `<c-filter_bar>`, `<c-data_grid>`, `<c-chart>`, `<c-modal>`, `<c-module_card>`, `<c-file_uploader>`).
- **Standardized Navigation & Clean Header Titles:** Unified `← Back` navigation via `<c-page_header back_url="..." />` across all views with short, clean module headers (`Q-Bank`, `Q-Mail`, `Q-Scan`, `Q-Verify`, `Q-Chat`).
- **Monochrome In-Development Cards:** In-development engines (`BUILDING`) render in clean, neutral monochrome black-and-white styling on the landing page.
- **Production-Ready Python Backend:** Powered by Django's ORM, services/selectors separation, atomic transactions, and analytical data pipelines.

---

## 2. Directory Architecture

```
Forensic-Q/
├── ForensiQ/                   # Django project configuration
│   ├── settings.py            # Global settings & apps sys.path setup
│   ├── urls.py                # Top-level URL routing
│   ├── asgi.py / wsgi.py
├── apps/                      # Modular Forensic Analytical Engines
│   ├── q_bank/                # Financial & bank statement ledger analysis
│   ├── q_chat/                # Corporate messaging & chat thread forensics
│   ├── q_ledger/              # ERP & financial records auditor (BUILDING)
│   ├── q_link/                # Cross-source evidence correlator (BUILDING)
│   ├── q_mail/                # Email & PST mailbox forensic extraction
│   ├── q_scan/                # Endpoint filesystem & keyword forensic triage
│   ├── q_trail/               # End-to-end money trail mapper (BUILDING)
│   ├── q_verify/              # Document metadata & authenticity verification
│   └── q_voice/               # Voice transcript intelligence analyzer (BUILDING)
├── core/                      # Core base models (ForensicBaseModel, TimeStampedModel) & utilities
│   ├── models.py
│   ├── middleware.py          # Master portal authentication middleware
│   ├── modules.py             # Dynamic module discovery catalog
│   ├── views.py               # Landing page, login & logout handlers
│   └── apps.py
├── demo/                      # Component sandbox & Tabulator demo
│   ├── views.py
│   ├── urls.py
│   ├── apps.py
│   └── templates/demo/        # Demo dashboard templates
│       ├── tabulator_demo.html# Forensic transaction ledger demo
│       └── test_dashboard.html# Component test sandbox
├── ui/                        # Centralized UI Design System & Cotton Components
│   ├── static/ui/             # Centralized design tokens & scripts
│   │   ├── css/theme.css      # Core tokens, Tabulator dark styling & scrollbars
│   │   └── js/
│   │       ├── tailwind-theme.js  # Tailwind CDN theme config & violet palette
│   │       └── theme-manager.js   # Synchronous theme init & dark/light switcher
│   ├── STYLE_GUIDE.md         # UI Style Guide & Cotton Component Catalog
│   ├── apps.py
│   └── templates/cotton/      # ALL REUSABLE COTTON COMPONENTS
│       ├── base.html          # Root shell, dark theme & theme switcher
│       ├── page_header.html   # Clean title, standardized back_url button & slot
│       ├── file_uploader.html # Standardized drag-and-drop file upload component
│       ├── stat_card.html     # KPI metric widgets (sky, emerald, amber, rose, slate)
│       ├── card.html          # Standard card containers
│       ├── filter_bar.html    # Multi-column instant filter toolbar
│       ├── badge.html         # Status & risk badges
│       ├── modal.html         # Forensic detail dossiers
│       ├── data_grid.html     # Tabulator.js data tables
│       ├── chart.html         # Plotly visualization containers
│       └── module_card.html   # Module card with live accents & monochrome BUILDING state
├── manage.py
├── pyproject.toml             # uv package dependencies
└── INSTRUCTIONS.md            # Developer instructions (this file)
```

---

## 3. Technology Stack

* **Runtime:** Python `>=3.13` managed with [`uv`](https://docs.astral.sh/uv/)
* **Web Framework:** Django `6.1.1`
* **Component Engine:** [`django-cotton`](https://django-cotton.com/) (`>=2.7.2`)
* **Interactive Data Grid:** [Tabulator.js](https://tabulator.info/) `v6.3.0`
* **Visualization:** `plotly` (`>=7.1.0`) + Plotly.js (`plotly_dark` theme)
* **Design & Styling:** Tailwind CSS (`dark:` mode class), FontAwesome 6, Aptos font, JetBrains Mono

---

## 4. Running the Workstation

Always execute commands with `uv run`:
```bash
# Apply database migrations
uv run python manage.py migrate

# Check for system configuration issues
uv run python manage.py check

# Run pre-commit quality & architecture validation
uv run python scripts/validate_project.py

# Run local development server
uv run python manage.py runserver 127.0.0.1:8000
```

### Endpoints & Access
* **Landing Platform:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Portal Login:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/) *(Password: `forensiq2026`)*
* **Q-Bank Multi-Bank Analyzer:** [http://127.0.0.1:8000/bank/](http://127.0.0.1:8000/bank/)
* **Q-Mail Investigation Hub:** [http://127.0.0.1:8000/mail/](http://127.0.0.1:8000/mail/)
* **Q-Chat Corporate Messaging:** [http://127.0.0.1:8000/chat/](http://127.0.0.1:8000/chat/)
* **Q-Verify Authenticity Verifier:** [http://127.0.0.1:8000/verify/](http://127.0.0.1:8000/verify/)
* **Q-Scan Endpoint Scanner:** [http://127.0.0.1:8000/scan/](http://127.0.0.1:8000/scan/)
* **Demo Forensic Ledger:** [http://127.0.0.1:8000/demo/tabulator/](http://127.0.0.1:8000/demo/tabulator/)
* **Demo Component Sandbox:** [http://127.0.0.1:8000/demo/sandbox/](http://127.0.0.1:8000/demo/sandbox/)

---

## 5. Building Forensic Dashboards with Cotton

Building a new dashboard page is simple and clean:

```html
<c-base title="ForensiQ | Entity Flow Ledger">

    <!-- 1. Standardized Page Header with Back Button -->
    <c-page_header 
        title="Entity Flow Ledger" 
        subtitle="Interactive audit of cross-source fund routing." 
        icon="fa-solid fa-network-wired"
        icon_color="text-amber-500"
        back_url="/">
        
        <button id="btn-export" class="px-3.5 py-2 bg-amber-500 text-zinc-950 font-bold rounded-xl text-xs shadow-md">
            <i class="fa-solid fa-file-csv mr-1.5"></i> Export CSV
        </button>
    </c-page_header>

    <!-- 2. KPI Metrics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <c-stat_card title="Volume" value="₹14.2M" variant="emerald" icon="fa-solid fa-arrow-trend-up" />
        <c-stat_card title="Flagged" value="12" variant="rose" icon="fa-solid fa-triangle-exclamation" />
        <c-stat_card title="Entities" value="84" variant="sky" icon="fa-solid fa-users" />
    </div>

    <!-- 3. Standardized File Uploader -->
    <div class="mb-6">
        <c-file_uploader 
            name="evidence_file"
            accept=".csv,.xlsx,.json"
            label="Forensic Ledger Evidence File"
            hint="Drag & drop evidence dataset or click to browse"
            badge="SHA-256 Validated"
            required />
    </div>

    <!-- 4. Visuals & Data Table -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <c-chart title="Outflow Distribution" :figure_html="chart_html" />
        <c-data_grid id="entity-grid" title="Entity Registry" :columns="columns_json" :data="data_json" />
    </div>

</c-base>
```

---

## 6. Critical Template & Cotton Rules

1. **Root Layout Component:** Use `<c-base title="...">` to wrap all dashboard pages.
2. **Standardized Header Navigation:** Always use `<c-page_header title="Q-Name" back_url="..." />` to render clean titles and the standardized `← Back` button.
3. **Centralized File Ingestion:** Always use `<c-file_uploader />` for file inputs instead of writing custom dropzone markup.
4. **Dynamic Props Binding:** Always use `:prop="variable"` for dynamic Django variables (e.g. `:figure_html="chart_html"` or `:data="table_data"`).
5. **Named Slots Syntax:** Always use `<c-slot name="...">` (e.g. `<c-slot name="actions">`). Never use `<c-slot:name>` (Windows compatibility).
6. **No `<c-` tags in HTML Comments:** Use `{% comment %}...{% endcomment %}` to avoid unclosed tag parse errors.

---

## 7. Dynamic Forensic Engine Registry (`apps/`)

All analytical modules placed in `apps/` are automatically discovered and rendered as interactive cards on the workstation landing page.

To configure an app's display card, define metadata attributes in its `AppConfig` (`apps/<app_name>/apps.py`):

```python
from django.apps import AppConfig


class QBankConfig(AppConfig):
    name = "q_bank"
    verbose_name = "Q-Bank"

    # Forensic Landing Page Card Metadata
    module_num = "01"
    module_category = "TRANSACTION"
    module_name = "Bank"
    module_tag = "LIVE"  # 'LIVE' for active engines, 'BUILDING' for in-development engines
    module_accent = "orange"  # orange, gold, purple, teal, rose, amber, steel, copper
    module_tagline = "Multi-Bank Forensic Analyzer"
    module_url = "/bank/"
    module_order = 1
```

*Monochrome Rule:* Cards with `module_tag = "BUILDING"` automatically render in clean black-and-white monochrome styling on the landing page.
*Grid Layout Rule:* If the total number of apps is not a multiple of 3, the final row automatically centers cards across the workstation grid.

---

## 8. Uniform Q-App Architecture & Terminology Standard (STRICT: NO Backward Compatibility Shims)

All Q-Apps (`q_bank`, `q_mail`, `q_scan`, `q_verify`, `q_voice`, `q_chat`, `q_ledger`) must strictly adhere to identical naming conventions for code files, templates, URLs, and UI terminology. 

**STRICT RULE:** **NO backward-compatibility shims allowed.** Do not create alias functions (`legacy_view = dashboard_view`), duplicate URL routes (`name="list"`, `name="landing"`), or legacy shim templates (`landing.html` including `dashboard.html`). Directly migrate all code to the uniform standard.

### 1. Code Files Architecture Standard
| Artifact Type | Standard Pattern | Example |
| :--- | :--- | :--- |
| **Main View Controller** | `def dashboard_view(request: HttpRequest) -> HttpResponse:` | In `views.py` across all apps |
| **Main URL Route** | `path("", views.dashboard_view, name="dashboard")` | In `urls.py` across all apps |
| **Main Hub Template** | `apps/<app_name>/templates/<app_name>/dashboard.html` | `q_mail/dashboard.html` |
| **Detail View Controller** | `def <entity>_detail_view(request, ...)` | `person_detail_view`, `investigation_detail_view` |
| **Detail URL Route** | `path("<entity>/<uuid:id>/", views.<entity>_detail_view, name="<entity>_detail")` | `name="investigation_detail"` |
| **Detail Template** | `apps/<app_name>/templates/<app_name>/<entity>_detail.html` | `case_detail.html`, `channel_detail.html` |
| **Service Layer** | `services.py` | Business workflows, writes, mutations |
| **Selector Layer** | `selectors.py` | Read-only ORM queries with N+1 elimination |
| **Data Models** | `models.py` | Declarative models inheriting `ForensicBaseModel` |

### 2. UI & Design Terminology Standard
| Component | Standard Terminology Pattern | Example |
| :--- | :--- | :--- |
| **Header Action Button** | `Import <Artifact Name>` | `Import Bank Statement`, `Import PST Mailbox`, `Import Scan Findings`, `New Verification Case`, `Import Audio Recording`, `Import Chat Export`, `Import SAP Records` |
| **Directory Section Header** | `<Entities> Directory` | `Target Auditees Directory`, `Audited Mailboxes Directory`, `Audited Endpoints Directory`, `Verification Cases Directory`, `Voice Recordings Directory`, `Audited Chat Channels Directory` |
| **Directory Search Bar** | `Search <entities> directory...` | Real-time Alpine filter, clear button, and `<N> Item(s) Configured` badge |
| **Profile Selector** | `<c-profile_selector label="Target Auditee / Investigation Profile" name="profile_id" ... />` | Standardized auditee dropdown + inline creation across all upload modals |
| **Profile Resolution** | `core.profiles.resolve_or_create_profile_from_request` | Automatically links or creates unified `InvestigationProfile` |

