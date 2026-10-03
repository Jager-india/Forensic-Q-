/**
 * Synchronize Top Pagination Controls with Tabulator's Bottom Footer
 * Creates a two-way mirrored pagination bar for large forensic grids.
 */
function setupTopPaginationSync(table, gridSelector, topContainerSelector) {
    const topContainer = document.querySelector(topContainerSelector);
    if (!topContainer) return;

    let isUpdating = false;

    function sync() {
        if (isUpdating) return;
        const bottomPaginator = document.querySelector(`${gridSelector} .tabulator-footer .tabulator-paginator`);
        if (!bottomPaginator) return;

        isUpdating = true;
        topContainer.innerHTML = bottomPaginator.innerHTML;

        const bottomSelect = bottomPaginator.querySelector('select.tabulator-page-size');
        const topSelect = topContainer.querySelector('select.tabulator-page-size');
        if (bottomSelect && topSelect) {
            topSelect.value = bottomSelect.value;
        }
        isUpdating = false;
    }

    topContainer.addEventListener('click', function(e) {
        const btn = e.target.closest('button.tabulator-page');
        if (!btn || btn.disabled) return;
        const pageAttr = btn.getAttribute('data-page');
        if (!pageAttr) return;

        if (pageAttr === 'first') {
            table.setPage(1);
        } else if (pageAttr === 'prev') {
            table.previousPage();
        } else if (pageAttr === 'next') {
            table.nextPage();
        } else if (pageAttr === 'last') {
            table.setPage(table.getPageMax());
        } else {
            const pageNum = parseInt(pageAttr, 10);
            if (!isNaN(pageNum)) {
                table.setPage(pageNum);
            }
        }
    });

    topContainer.addEventListener('change', function(e) {
        const select = e.target.closest('select.tabulator-page-size');
        if (select) {
            const size = parseInt(select.value, 10);
            if (!isNaN(size)) {
                table.setPageSize(size);
            }
        }
    });

    table.on("pageLoaded", function() { setTimeout(sync, 20); });
    table.on("dataLoaded", function() { setTimeout(sync, 20); });
    table.on("renderComplete", function() { setTimeout(sync, 20); });
    table.on("tableBuilt", function() { setTimeout(sync, 50); });

    const gridEl = document.querySelector(gridSelector);
    if (gridEl) {
        const observer = new MutationObserver(function() {
            sync();
        });
        observer.observe(gridEl, { childList: true, subtree: true });
    }

    setTimeout(sync, 100);
}

window.setupTopPaginationSync = setupTopPaginationSync;
