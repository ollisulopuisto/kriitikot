
document.addEventListener('DOMContentLoaded', () => {
    const tableWrapper = document.querySelector('.table-wrapper');

    // Check if the table wrapper exists and we are on a desktop view
    if (!tableWrapper || window.innerWidth <= 768) {
        return;
    }

    let scrollTimeout;

    // This is the column we want to scroll past.
    const movieTitleHeader = document.querySelector('th.movie-col');
    if (!movieTitleHeader) {
        return;
    }

    // Calculate the target scroll position.
    // We want to scroll just enough to hide the movie title column.
    const targetScrollLeft = movieTitleHeader.offsetWidth;

    window.addEventListener('scroll', () => {
        // Clear the previous timeout to reset the timer
        clearTimeout(scrollTimeout);

        // Set a new timeout
        scrollTimeout = setTimeout(() => {
            // Check if the user has scrolled down past the header
            if (window.scrollY > 200) {
                // Check if the table is not already scrolled enough
                if (tableWrapper.scrollLeft < targetScrollLeft) {
                    tableWrapper.scrollTo({
                        left: targetScrollLeft,
                        behavior: 'smooth'
                    });
                }
            }
        }, 150); // A 150ms delay to wait for scrolling to stop
    });
});
