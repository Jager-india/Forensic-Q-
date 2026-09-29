# `ui` — User Guide & Page Composition Cookbook

## 1. Quick Start: Building a Forensic Dashboard Page

To construct a new forensic dashboard view, assemble components inside your app's template:

```html
<c-base title="ForensiQ | Entity Flow Ledger">

    <!-- 1. Header Toolbar with Standardized Back Navigation -->
    <c-page_header 
        title="Q-Link" 
        subtitle="Cross-account fund movement and flagged counterparty correlation."
        icon="fa-solid fa-network-wired"
        icon_color="text-amber-500"
        back_url="/">
        
        <button class="px-3.5 py-2 bg-amber-500 text-zinc-950 font-bold rounded-lg text-xs">
            <i class="fa-solid fa-file-csv mr-1"></i> Export Report
        </button>
    </c-page_header>

    <!-- 2. Metric KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <c-stat_card title="Total Transferred" value="₹18.4M" variant="emerald" icon="fa-solid fa-arrow-trend-up" />
        <c-stat_card title="Flagged Layering" value="7" variant="rose" icon="fa-solid fa-triangle-exclamation" />
        <c-stat_card title="Unique Entities" value="42" variant="sky" icon="fa-solid fa-users" />
    </div>

    <!-- 3. Centralized Evidence File Uploader -->
    <div class="mb-6">
        <c-file_uploader 
            name="link_dataset"
            accept=".csv,.xlsx,.json"
            label="Transaction Network Evidence File"
            hint="Drag & drop entity correlation data or click to browse"
            badge="SHA-256 Validated"
            required />
    </div>

    <!-- 4. Charts & Data Tables -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <c-chart title="Outflow Distribution" :figure_html="chart_html" />
        <c-data_grid id="entity-grid" title="Entity Registry" :columns="columns_json" :data="data_json" />
    </div>

</c-base>
```

