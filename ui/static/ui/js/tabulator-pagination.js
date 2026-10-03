/**
 * Automatic Top Pagination for Tabulator Tables
 * Centralized in ForensiQ UI component system.
 * Automatically mirrors bottom pagination controls to the top for all tables configured with pagination.
 */
(function () {
    if (typeof window === "undefined") return;

    function hasPaginationConfig(options) {
        if (!options) return false;
        if (options.pagination === false || options.pagination === "none") return false;
        return !!(
            options.pagination === true ||
            options.pagination === "local" ||
            options.pagination === "remote" ||
            options.paginationMode === "local" ||
            options.paginationMode === "remote" ||
            options.paginationSize ||
            options.paginationSizeSelector
        );
    }

    function setupAutoTopPagination(table) {
        function init() {
            const gridEl = table.element;
            if (!gridEl || !gridEl.parentNode) return;
            if (gridEl._hasAutoTopPagination) return;
            gridEl._hasAutoTopPagination = true;

            // Locate or create the top pagination wrapper
            let topWrapper = gridEl.previousElementSibling;
            let topContainer = null;

            if (topWrapper && topWrapper.classList.contains("tabulator-top-pagination-bar")) {
                topContainer = topWrapper.querySelector(".tabulator-top-paginator");
            } else if (topWrapper && topWrapper.querySelector(".tabulator-paginator")) {
                topContainer = topWrapper.querySelector(".tabulator-paginator");
            } else {
                topWrapper = document.createElement("div");
                topWrapper.className = "tabulator-top-pagination-bar flex items-center justify-end mb-2.5";
                topWrapper.innerHTML = `
                    <div class="tabulator border-0 bg-transparent">
                        <div class="tabulator-footer border-0 bg-transparent p-0">
                            <div class="tabulator-top-paginator tabulator-paginator flex flex-wrap items-center gap-1 text-xs text-slate-500 dark:text-zinc-400 select-none"></div>
                        </div>
                    </div>
                `;
                gridEl.parentNode.insertBefore(topWrapper, gridEl);
                topContainer = topWrapper.querySelector(".tabulator-top-paginator");
            }

            if (!topContainer) return;

            let isUpdating = false;

            function sync() {
                if (isUpdating) return;
                const bottomPaginator = gridEl.querySelector(".tabulator-footer .tabulator-paginator");
                if (!bottomPaginator) {
                    topWrapper.style.display = "none";
                    return;
                }

                if (!bottomPaginator.children.length && !bottomPaginator.textContent.trim()) {
                    topWrapper.style.display = "none";
                    return;
                }
                topWrapper.style.display = "flex";

                isUpdating = true;
                topContainer.innerHTML = bottomPaginator.innerHTML;

                const bottomSelect = bottomPaginator.querySelector("select.tabulator-page-size");
                const topSelect = topContainer.querySelector("select.tabulator-page-size");
                if (bottomSelect && topSelect) {
                    topSelect.value = bottomSelect.value;
                }
                isUpdating = false;
            }

            topContainer.addEventListener("click", function (e) {
                const btn = e.target.closest("button.tabulator-page");
                if (!btn || btn.disabled) return;
                const pageAttr = btn.getAttribute("data-page");
                if (!pageAttr) return;

                if (pageAttr === "first") {
                    table.setPage(1);
                } else if (pageAttr === "prev") {
                    table.previousPage();
                } else if (pageAttr === "next") {
                    table.nextPage();
                } else if (pageAttr === "last") {
                    table.setPage(table.getPageMax());
                } else {
                    const pageNum = parseInt(pageAttr, 10);
                    if (!isNaN(pageNum)) {
                        table.setPage(pageNum);
                    }
                }
            });

            topContainer.addEventListener("change", function (e) {
                const select = e.target.closest("select.tabulator-page-size");
                if (select) {
                    const size = parseInt(select.value, 10);
                    if (!isNaN(size)) {
                        table.setPageSize(size);
                    }
                }
            });

            table.on("pageLoaded", function () { setTimeout(sync, 20); });
            table.on("dataLoaded", function () { setTimeout(sync, 20); });
            table.on("renderComplete", function () { setTimeout(sync, 20); });

            const observer = new MutationObserver(sync);
            observer.observe(gridEl, { childList: true, subtree: true });

            setTimeout(sync, 50);
            setTimeout(sync, 150);
            setTimeout(sync, 300);
        }

        if (table.element && table.element.querySelector(".tabulator-footer")) {
            init();
        } else {
            table.on("tableBuilt", init);
        }
    }

    function initAutoPagination() {
        const OriginalTabulator = window.Tabulator;
        if (!OriginalTabulator || OriginalTabulator._autoPaginationWrapped) return;

        function AutoTabulator(...args) {
            let instance;
            try {
                instance = Reflect.construct(OriginalTabulator, args, AutoTabulator);
            } catch (err) {
                instance = new OriginalTabulator(...args);
            }

            const options = args[1];
            if (hasPaginationConfig(options)) {
                setupAutoTopPagination(instance);
            }

            return instance;
        }

        AutoTabulator.prototype = OriginalTabulator.prototype;
        Object.assign(AutoTabulator, OriginalTabulator);
        AutoTabulator._autoPaginationWrapped = true;

        window.Tabulator = AutoTabulator;
    }

    initAutoPagination();
    document.addEventListener("DOMContentLoaded", initAutoPagination);

    // Backward-compatibility export
    window.setupTopPaginationSync = function (table, gridSelector, topContainerSelector) {
        if (!table) return;
        const gridEl = typeof gridSelector === "string" ? document.querySelector(gridSelector) : gridSelector;
        const topContainer = typeof topContainerSelector === "string" ? document.querySelector(topContainerSelector) : topContainerSelector;
        if (gridEl && topContainer && !gridEl._hasAutoTopPagination) {
            setupAutoTopPagination(table);
        }
    };
})();
