# `ui` — Developer Instructions & Architecture Guide

## 1. Overview & Purpose
The `ui` application contains the standardized **ForensiQ Design System** and **Django Cotton Component Suite** (`ui/templates/cotton/`).

All dashboard views across all analytical modules (`q_bank`, `q_mail`, `q_trail`, etc.) MUST use the reusable Cotton components in `ui/templates/cotton/` to guarantee visual consistency.

---

## 2. Directory Structure
```
ui/
├── STYLE_GUIDE.md            # Comprehensive color token & typography manual
├── INSTRUCTION.md            # Developer guide (this file)
├── SCHEMA.md                 # Component prop signatures & slot specifications
├── USER_GUIDE.md             # How to build pages using Cotton tags
├── static/ui/                # Centralized theme tokens and scripts
│   ├── css/theme.css         # Theme CSS, Tabulator dark styling, Aptos typography
│   └── js/
│       ├── tailwind-theme.js # Tailwind CSS theme configuration & palettes
│       └── theme-manager.js  # Theme initialization & dark/light switcher
└── templates/cotton/         # ALL REUSABLE COTTON COMPONENTS
    ├── base.html             # Root shell with dark violet theme & header
    ├── page_header.html      # Clean title, standardized back_url navigation & action toolbar
    ├── file_uploader.html    # Standardized drag-and-drop file upload component
    ├── stat_card.html        # KPI metric widgets (sky, emerald, amber, rose, slate)
    ├── card.html             # Standard card containers
    ├── filter_bar.html       # Multi-column instant filter toolbar
    ├── badge.html            # Status & risk badges
    ├── modal.html            # Forensic detail dossiers
    ├── data_grid.html        # Tabulator.js data tables
    ├── chart.html            # Plotly visualization containers
    └── module_card.html      # Forensic engine landing card with monochrome BUILDING state
```

---

## 3. Strict Rules for Interns & Vibe-Coding

> [!CRITICAL]
> **Rule 1: Always Register Reusable UI in `ui/templates/cotton/`**
> Never write custom container styles or one-off table wrappers in individual apps. All reusable components must live in `ui/templates/cotton/`.

> [!CRITICAL]
> **Rule 2: Never Use Windows Colon Syntax**
> Use `<c-slot name="actions">`. Never use `<c-slot:actions>` (triggers `[WinError 123]` on Windows systems).

> [!CRITICAL]
> **Rule 3: Use Centralized Design Tokens & Aptos Font**
> Use curated tokens defined in `ui/static/ui/css/theme.css`:
> * Dark Canvas Background: `dark:bg-[#502D55]` (`#502D55`)
> * Card Surface: `dark:bg-[#3d2042]` / `dark:bg-zinc-900`
> * Border: `dark:border-[#6b3d72]` / `dark:border-zinc-800`
> * Brand Accent: `text-amber-500` / `bg-amber-500` (`#f59e0b`)
> * Standard Typography: Aptos (`font-sans`) and JetBrains Mono (`font-mono`)

> [!CRITICAL]
> **Rule 4: Standardize Navigation & Ingestion**
> * Always include `<c-page_header title="Q-Name" back_url="/" />` on all module pages.
> * Always use `<c-file_uploader />` for data ingestion rather than ad-hoc file upload forms.
