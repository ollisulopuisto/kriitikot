document.addEventListener('DOMContentLoaded', () => {
    const tableWrapper = document.querySelector('.table-wrapper');

    if (!tableWrapper || window.innerWidth <= 768) {
        return;
    }

    let scrollTimeout;
    const stickyColumn = document.querySelector('th.movie-col');
    if (!stickyColumn) return;

    const criticHeaders = Array.from(document.querySelectorAll('thead th.rating-cell'));
    const movieRows = Array.from(document.querySelectorAll('tbody tr'));

    const columnsWithReviews = criticHeaders.map((header, index) => {
        for (const row of movieRows) {
            const cell = row.cells[index + 1];
            if (cell && cell.innerHTML.trim() !== '') {
                return true;
            }
        }
        return false;
    });

    window.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);

        scrollTimeout = setTimeout(() => {
            if (window.scrollY <= 200) {
                return;
            }

            const stickyWidth = stickyColumn.offsetWidth;
            const scrollLeft = tableWrapper.scrollLeft;
            const viewportWidth = tableWrapper.clientWidth;

            // The "effective" viewport is the visible area to the right of the sticky column.
            const effectiveViewportStart = scrollLeft + stickyWidth;
            const effectiveViewportEnd = scrollLeft + viewportWidth;

            let reviewInView = false;
            for (let i = 0; i < criticHeaders.length; i++) {
                if (!columnsWithReviews[i]) continue;

                const header = criticHeaders[i];
                const headerStart = header.offsetLeft;
                const headerEnd = headerStart + header.offsetWidth;

                // Check if any part of a column with a review overlaps with the effective viewport.
                if (headerEnd > effectiveViewportStart && headerStart < effectiveViewportEnd) {
                    reviewInView = true;
                    break;
                }
            }

            if (!reviewInView) {
                // Find the first column with a review that is to the right of the current view.
                let targetColumn = null;
                for (let i = 0; i < criticHeaders.length; i++) {
                    if (!columnsWithReviews[i]) continue;

                    const header = criticHeaders[i];
                    // Find the first review column that starts at or after the beginning of the effective viewport.
                    if (header.offsetLeft >= scrollLeft + stickyWidth) {
                         targetColumn = header;
                         break;
                    }
                }

                if (targetColumn) {
                    // We want the target column's left edge to be where the sticky column ends.
                    // The new scrollLeft should be target.offsetLeft - stickyWidth.
                    const newScrollLeft = targetColumn.offsetLeft - stickyWidth;

                    tableWrapper.scrollTo({
                        left: newScrollLeft,
                        behavior: 'smooth'
                    });
                }
            }

        }, 250);
    });
});
