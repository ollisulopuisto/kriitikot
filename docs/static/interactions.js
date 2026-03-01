// Kriitikon valinta - Sorting and Click Handlers
// ===============================================

/**
 * Ylänurkka: Aakkosta elokuvat ja kriitikot
 */
function initSorting() {
    const table = document.querySelector('table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const sortMoviesBtn = document.getElementById('sort-movies-btn');
    const sortCriticsBtn = document.getElementById('sort-critics-btn');
    
    // Prevent double initialization
    if (sortMoviesBtn && sortMoviesBtn.dataset.initialized) return;

    let sortAscending = true;
    let sortCriticAscending = true;

    // Elokuvanimi sort
    function sortMovies() {
        // Remove open poster rows before sorting to prevent orphans and crashes
        tbody.querySelectorAll('.poster-row').forEach(row => row.remove());

        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => {
            const titleA = a.querySelector('.movie-col').textContent.trim();
            const titleB = b.querySelector('.movie-col').textContent.trim();
            if (sortAscending) {
                return titleA.localeCompare(titleB, 'fi');
            } else {
                return titleB.localeCompare(titleA, 'fi');
            }
        });
        rows.forEach(row => tbody.appendChild(row));
        sortAscending = !sortAscending;

        if (typeof sortCriticColumnsByReviews === 'function') {
            sortCriticColumnsByReviews();
            if (typeof updateCriticColumnVisibility === 'function') {
                updateCriticColumnVisibility();
            }
        }

        // Päivitä sticky header
        document.dispatchEvent(new CustomEvent('table-sorted'));

        sortMoviesBtn.classList.add('active');
        setTimeout(() => sortMoviesBtn.classList.remove('active'), 300);
    }

    if (sortMoviesBtn) {
        sortMoviesBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            sortMovies();
        });
        sortMoviesBtn.dataset.initialized = 'true';
    }

    // Kriitikonimi sort
    function sortCritics() {
        const theadRow = table.querySelector('thead tr:last-child');
        const criticHeaders = Array.from(theadRow.querySelectorAll('th.rating-cell'));

        const critics = criticHeaders.map((th, idx) => ({
            name: th.textContent.trim(),
            idx: idx
        }));

        critics.sort((a, b) => {
            if (sortCriticAscending) {
                return a.name.localeCompare(b.name, 'fi');
            } else {
                return b.name.localeCompare(a.name, 'fi');
            }
        });

        // Rearrange header
        critics.forEach((c, newIdx) => {
            theadRow.appendChild(criticHeaders[c.idx]);
        });

        // Rearrange each row's critic cells
        const rows = Array.from(tbody.querySelectorAll('tr:not(.poster-row)'));
        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td.rating-cell'));
            critics.forEach((c, newIdx) => {
                row.appendChild(cells[c.idx]);
            });
        });

        sortCriticAscending = !sortCriticAscending;

        // Päivitä sticky header
        document.dispatchEvent(new CustomEvent('table-sorted'));

        sortCriticsBtn.classList.add('active');
        setTimeout(() => sortCriticsBtn.classList.remove('active'), 300);
    }

    if (sortCriticsBtn) {
        sortCriticsBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            sortCritics();
        });
        sortCriticsBtn.dataset.initialized = 'true';
    }

    // Mobiili: Aakkosta elokuvakortit
    const mobileSortButton = document.getElementById('mobile-sort');
    const mobileCardsContainer = document.querySelector('.mobile-cards');
    if (mobileSortButton && mobileCardsContainer && !mobileSortButton.dataset.initialized) {
        let mobileSortAscending = true;
        mobileSortButton.addEventListener('click', function () {
            const cards = Array.from(mobileCardsContainer.querySelectorAll('.movie-card'));
            cards.sort((a, b) => {
                const titleA = a.querySelector('.movie-card-title').textContent.replace('🎬 ', '').trim();
                const titleB = b.querySelector('.movie-card-title').textContent.replace('🎬 ', '').trim();
                if (mobileSortAscending) {
                    return titleA.localeCompare(titleB, 'fi');
                } else {
                    return titleB.localeCompare(titleA, 'fi');
                }
            });
            cards.forEach(card => mobileCardsContainer.appendChild(card));
            mobileSortAscending = !mobileSortAscending;
            mobileSortButton.innerHTML = `<span class="sort-icon">🎬 ${mobileSortAscending ? 'A-Ö' : 'Ö-A'}</span>`;
        });
        mobileSortButton.dataset.initialized = 'true';
    }

    // Järjestä kriitikkosarakkeet arvioiden mukaan sivun latauksen yhteydessä
    if (typeof sortCriticColumnsByReviews === 'function') {
        sortCriticColumnsByReviews();
        if (typeof updateCriticColumnVisibility === 'function') {
            updateCriticColumnVisibility();
        }
    }
}

/**
 * Elokuvanimi click handler
 */
function initMovieClickHandlers() {
    const table = document.querySelector('table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    // Tallenna jokaisen elokuvasolun alkuperäinen sisältö, jotta se voidaan palauttaa
    tbody.querySelectorAll('.movie-col').forEach(cell => {
        if (!cell.__originalContent) {
            cell.__originalContent = cell.innerHTML;
        }
    });

    tbody.querySelectorAll('.movie-col:not([data-initialized])').forEach((movieCell) => {
        movieCell.style.cursor = 'pointer';
        movieCell.title = 'Klikkaa korostaaksesi tämän elokuvan arvostelut';

        movieCell.addEventListener('click', function () {
            const row = movieCell.parentElement;

            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();

            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }

            // Poista vanhat poster-rivit
            tbody.querySelectorAll('.poster-row').forEach(row => row.remove());

            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');
            const allCriticHeaders = table.querySelectorAll('thead th.rating-cell');

            // Tallenna alkuperäinen taulukon leveys
            if (!window.originalTableWidth) {
                window.originalTableWidth = table.offsetWidth;
            }

            // Tallenna ja nollaa skrollaus
            const tableWrapper = document.querySelector('.table-wrapper');
            if (tableWrapper) {
                window.savedScrollLeft = tableWrapper.scrollLeft;
                const originalScrollBehavior = tableWrapper.style.scrollBehavior;
                tableWrapper.style.scrollBehavior = 'auto';
                tableWrapper.scrollLeft = 0;
                setTimeout(() => {
                    tableWrapper.style.scrollBehavior = originalScrollBehavior;
                }, 50);
            }

            // Himmennä muut rivit
            allRows.forEach(r => {
                if (r !== row) {
                    r.classList.add('dimmed');
                    setTimeout(() => {
                        if (r.classList.contains('dimmed')) {
                            r.style.display = 'none';
                        }
                    }, 150);
                }
            });

            // Piilota kriitikkosarakkeet ilman arvostelua
            const ratingCells = row.querySelectorAll('.rating-cell');

            allCriticHeaders.forEach((header, colIndex) => {
                const cell = ratingCells[colIndex];

                if (cell) {
                    const hasLink = cell.querySelector('a.rating-link');
                    const hasStars = cell.querySelector('.rating-stars');
                    const noRating = cell.querySelector('.no-rating');
                    const isEmpty = noRating && noRating.textContent.trim() === '–';

                    if (!hasLink && !hasStars && isEmpty) {
                        header.classList.add('filter-hidden');
                        setTimeout(() => {
                            if (header.classList.contains('filter-hidden')) {
                                header.style.display = 'none';
                            }
                        }, 150);

                        allRows.forEach(r => {
                            const cells = r.querySelectorAll('.rating-cell');
                            if (cells[colIndex]) {
                                cells[colIndex].classList.add('filter-hidden');
                                setTimeout(() => {
                                    if (cells[colIndex].classList.contains('filter-hidden')) {
                                        cells[colIndex].style.display = 'none';
                                    }
                                }, 150);
                            }
                        });
                    }
                }
            });

            row.dataset.filtered = 'true';
            movieCell.classList.add('selected');

            // Lisää linkit elokuvan nimen / laskurin alapuolelle koskematta alkuperäiseen rakenteeseen
            const nytleffaanUrl = movieCell.dataset.nytleffaan;
            const letterboxdUrl = movieCell.dataset.letterboxd;
            const existingLinks = movieCell.querySelector('.movie-links');

            if (!existingLinks && (nytleffaanUrl || letterboxdUrl)) {
                const linksDiv = document.createElement('div');
                linksDiv.className = 'movie-links';
                linksDiv.style.marginTop = '0.5rem';

                if (nytleffaanUrl) {
                    const nytleffaanLink = document.createElement('a');
                    nytleffaanLink.href = nytleffaanUrl;
                    nytleffaanLink.target = '_blank';
                    nytleffaanLink.innerHTML = '🎬 Osta liput';
                    nytleffaanLink.className = 'movie-link nytleffaan-link';
                    nytleffaanLink.title = 'Osta liput: nytleffaan.fi';
                    linksDiv.appendChild(nytleffaanLink);
                }

                if (letterboxdUrl) {
                    const letterboxdLink = document.createElement('a');
                    letterboxdLink.href = letterboxdUrl;
                    letterboxdLink.target = '_blank';
                    letterboxdLink.textContent = '📽️ Letterboxd';
                    letterboxdLink.className = 'movie-link letterboxd-link';
                    linksDiv.appendChild(letterboxdLink);
                }

                const insertAfterTarget = movieCell.querySelector('.movie-review-count') || movieCell.querySelector('.movie-title-main');
                if (insertAfterTarget) {
                    insertAfterTarget.insertAdjacentElement('afterend', linksDiv);
                } else {
                    movieCell.appendChild(linksDiv);
                }
            }

            // Luo poster-rivi vain jos on poster
            const posterUrl = movieCell.dataset.poster;
            if (posterUrl) {
                const posterRow = document.createElement('tr');
                posterRow.className = 'poster-row';

                const posterCell = document.createElement('td');
                posterCell.colSpan = 1;

                const posterImg = document.createElement('img');
                posterImg.src = posterUrl;
                posterImg.alt = 'Elokuvan juliste';
                posterImg.className = 'movie-poster-inline';
                posterCell.appendChild(posterImg);

                posterRow.appendChild(posterCell);

                const columnCount = table.querySelectorAll('thead th').length;
                for (let i = 1; i < columnCount; i++) {
                    const emptyCell = document.createElement('td');
                    emptyCell.className = 'poster-row-empty';
                    posterRow.appendChild(emptyCell);
                }

                row.parentNode.insertBefore(posterRow, row.nextSibling);
            }

            if (typeof updateCriticColumnVisibility === 'function') {
                setTimeout(() => {
                    updateCriticColumnVisibility();
                }, 200);
            }

            setTimeout(() => {
                if (window.addFillerColumns) window.addFillerColumns();
            }, 200);

            if (window.showResetButton) window.showResetButton();
        });
        movieCell.dataset.initialized = 'true';
    });
}

/**
 * Kriitikon nimi click handler (Suodatus)
 */
function initCriticClickHandlers() {
    const table = document.querySelector('table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const criticHeaders = table.querySelectorAll('thead th.rating-cell');

    criticHeaders.forEach((criticHeader) => {
        if (criticHeader.dataset.initialized) return;
        
        criticHeader.style.cursor = 'pointer';
        criticHeader.title = 'Klikkaa näyttääksesi vain tämän kriitikon arvostelut';

        criticHeader.addEventListener('click', function () {
            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();

            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }

            // Poista vanhat poster-rivit
            tbody.querySelectorAll('.poster-row').forEach(row => row.remove());

            const allCriticHeaders = table.querySelectorAll('thead th.rating-cell');
            const colIndex = Array.prototype.indexOf.call(allCriticHeaders, criticHeader);

            // Tallenna ja nollaa skrollaus
            const tableWrapper = document.querySelector('.table-wrapper');
            if (tableWrapper) {
                window.savedScrollLeft = tableWrapper.scrollLeft;
                const originalScrollBehavior = tableWrapper.style.scrollBehavior;
                tableWrapper.style.scrollBehavior = 'auto';
                tableWrapper.scrollLeft = 0;
                setTimeout(() => {
                    tableWrapper.style.scrollBehavior = originalScrollBehavior;
                }, 50);
            }

            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');

            // Piilota muut kriitikkosarakkeet
            allCriticHeaders.forEach((header, idx) => {
                if (idx !== colIndex) {
                    header.classList.add('filter-hidden');
                    setTimeout(() => {
                        if (header.classList.contains('filter-hidden')) {
                            header.style.display = 'none';
                        }
                    }, 150);

                    allRows.forEach(row => {
                        const cells = row.querySelectorAll('.rating-cell');
                        if (cells[idx]) {
                            cells[idx].classList.add('filter-hidden');
                            setTimeout(() => {
                                if (cells[idx].classList.contains('filter-hidden')) {
                                    cells[idx].style.display = 'none';
                                }
                            }, 150);
                        }
                    });
                }
            });

            // Piilota rivit ilman arviota tältä kriitikolta
            allRows.forEach(row => {
                const cells = row.querySelectorAll('.rating-cell');
                const cell = cells[colIndex];

                if (cell) {
                    const hasLink = cell.querySelector('a.rating-link');
                    const hasStars = cell.querySelector('.rating-stars');
                    const noRating = cell.querySelector('.no-rating');
                    const isEmpty = noRating && noRating.textContent.trim() === '–';

                    if (!hasLink && !hasStars && isEmpty) {
                        row.classList.add('dimmed');
                        setTimeout(() => {
                            if (row.classList.contains('dimmed')) {
                                row.style.display = 'none';
                            }
                        }, 150);
                    }
                }
            });

            // Merkitse suodatus aktiiviseksi
            criticHeader.classList.add('selected');
            criticHeader.dataset.filtered = 'true';

            if (typeof updateCriticColumnVisibility === 'function') {
                setTimeout(() => {
                    updateCriticColumnVisibility();
                }, 200);
            }

            setTimeout(() => {
                if (window.removeFillerColumns) window.removeFillerColumns();
                if (window.addFillerColumns) window.addFillerColumns();
            }, 250);

            if (window.showResetButton) window.showResetButton();
        });
        criticHeader.dataset.initialized = 'true';
    });
}

/**
 * Mobile: Kriitikon nimi-alue click handler
 */
function initMobileCriticClickHandlers() {
    const reviewItems = document.querySelectorAll('.review-item');

    reviewItems.forEach(reviewItem => {
        // Prevent double initialization
        if (reviewItem.dataset.initialized) return;

        const criticArea = reviewItem.querySelector('.review-critic');
        if (!criticArea) return;

        const criticName = reviewItem.querySelector('.review-critic-name');

        criticArea.style.cursor = 'pointer';
        criticArea.style.userSelect = 'none';
        criticArea.title = 'Klikkaa nähdäksesi vain tämän kriitikon arvostelut';

        criticArea.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();

            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }

            const selectedCritic = reviewItem.dataset.critic;
            const allCards = document.querySelectorAll('.movie-card');
            const allReviewItems = document.querySelectorAll('.review-item');

            allCards.forEach(card => {
                const cardHasSelectedCritic = Array.from(card.querySelectorAll('.review-item'))
                    .some(item => item.dataset.critic === selectedCritic);

                if (!cardHasSelectedCritic) {
                    card.style.display = 'none';
                } else {
                    card.style.display = '';
                    card.querySelectorAll('.review-item').forEach(item => {
                        if (item.dataset.critic !== selectedCritic) {
                            item.style.display = 'none';
                        }
                    });
                }
            });

            allReviewItems.forEach(item => {
                const area = item.querySelector('.review-critic');
                const name = item.querySelector('.review-critic-name');
                if (area && name && item.dataset.critic === selectedCritic) {
                    name.classList.add('selected');
                    area.dataset.filtered = 'true';
                }
            });

            const criticFilterValue = document.getElementById('critic-filter-value-mobile');
            if (criticFilterValue) {
                // Show the critic's display name (not the internal id) in the mobile filter UI
                const displayName = (criticName && criticName.textContent) ? criticName.textContent.trim() : selectedCritic;
                criticFilterValue.textContent = displayName;
            }

            if (window.showResetButton) window.showResetButton();
        });
        reviewItem.dataset.initialized = 'true';
    });
}

/**
 * Footer: Tähtijakauma click handlers
 */
function initRatingFilterClickHandlers() {
    const ratingFilters = document.querySelectorAll('.filter-rating');
    ratingFilters.forEach(ratingFilter => {
        if (ratingFilter.dataset.initialized) return;
        
        ratingFilter.addEventListener('click', function (e) {
            e.preventDefault();

            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();

            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }

            const selectedStars = parseInt(this.dataset.stars);
            const allCards = document.querySelectorAll('.movie-card');

            const tableWrapper = document.querySelector('.table-wrapper');
            if (tableWrapper) {
                window.savedScrollLeft = tableWrapper.scrollLeft;
                const originalScrollBehavior = tableWrapper.style.scrollBehavior;
                tableWrapper.style.scrollBehavior = 'auto';
                tableWrapper.scrollLeft = 0;
                setTimeout(() => {
                    tableWrapper.style.scrollBehavior = originalScrollBehavior;
                }, 50);
            }

            // Mobile
            allCards.forEach(card => {
                const cardReviews = card.querySelectorAll('.review-item');
                let hasMatchingReview = false;

                cardReviews.forEach(item => {
                    const ratingElement = item.querySelector('.review-rating a, .review-rating');
                    const ratingText = ratingElement ? ratingElement.textContent.trim() : '';
                    const starCount = (ratingText.match(/★/g) || []).length;

                    if (starCount === selectedStars) {
                        hasMatchingReview = true;
                        item.style.display = '';
                        item.classList.remove('dimmed');
                    } else {
                        item.style.display = ''; // Näytetään, mutta himmennettynä
                        item.classList.add('dimmed');
                    }
                });

                card.style.display = hasMatchingReview ? '' : 'none';
            });

            // Desktop
            const table = document.querySelector('table');
            if (table) {
                const tbody = table.querySelector('tbody');
                const allRows = tbody.querySelectorAll('tr');

                allRows.forEach(row => {
                    const ratingCells = row.querySelectorAll('.rating-cell');
                    let hasMatchingRating = false;

                    ratingCells.forEach(cell => {
                        const ratingSpan = cell.querySelector('.rating-stars');
                        if (ratingSpan) {
                            const starCount = (ratingSpan.textContent.match(/★/g) || []).length;
                            if (starCount === selectedStars) {
                                hasMatchingRating = true;
                                cell.classList.remove('dimmed');
                            } else {
                                cell.classList.add('dimmed');
                            }
                        } else {
                            cell.classList.add('dimmed');
                        }
                    });

                    row.style.display = hasMatchingRating ? '' : 'none';
                });

                if (typeof updateCriticColumnVisibility === 'function') {
                    setTimeout(() => {
                        updateCriticColumnVisibility();
                    }, 200);
                }

                // Poista vanhat täytesarakkeet ensin, sitten lisää uudet
                setTimeout(() => {
                    if (window.removeFillerColumns) window.removeFillerColumns();
                    if (window.addFillerColumns) window.addFillerColumns();
                }, 250);
            }

            this.style.backgroundColor = '#f0e6ff';
            this.style.fontWeight = 'bold';

            if (window.showResetButton) window.showResetButton();
        });
        ratingFilter.dataset.initialized = 'true';
    });
}

/**
 * Footer: Julkaisut click handlers
 */
function initPublicationFilterClickHandlers() {
    const publicationFilters = document.querySelectorAll('.filter-publication');
    let activePublications = [];

    publicationFilters.forEach(pubFilter => {
        if (pubFilter.dataset.initialized) return;
        
        pubFilter.addEventListener('click', function (e) {
            e.preventDefault();

            const selectedPub = this.dataset.publication;
            const index = activePublications.indexOf(selectedPub);

            if (index > -1) {
                activePublications.splice(index, 1);
                this.classList.remove('selected');
                this.style.backgroundColor = '';
                this.style.fontWeight = '';
            } else {
                activePublications.push(selectedPub);
                this.classList.add('selected');
                this.style.backgroundColor = '#f0e6ff';
                this.style.fontWeight = 'bold';
            }

            applyPublicationFilter(activePublications);

            if (activePublications.length > 0) {
                if (window.showResetButton) window.showResetButton();
            }
        });
        pubFilter.dataset.initialized = 'true';
    });

    function applyPublicationFilter(publications) {
        const allCards = document.querySelectorAll('.movie-card');
        const table = document.querySelector('table');
        const noFilter = publications.length === 0;

        // Mobile
        allCards.forEach(card => {
            const cardReviews = card.querySelectorAll('.review-item');
            let hasMatchingReview = false;

            cardReviews.forEach(item => {
                if (noFilter) {
                    item.style.display = '';
                } else {
                    const mediaElement = item.querySelector('.review-media');
                    const mediaText = mediaElement ? mediaElement.textContent.trim().replace('/ ', '') : '';
                    if (publications.includes(mediaText)) {
                        item.style.display = '';
                        hasMatchingReview = true;
                    } else {
                        item.style.display = 'none';
                    }
                }
            });

            if (noFilter) {
                card.style.display = '';
            } else {
                card.style.display = hasMatchingReview ? '' : 'none';
            }
        });

        // Desktop
        if (table) {
            const tbody = table.querySelector('tbody');
            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');

            allRows.forEach(row => {
                const ratingCells = row.querySelectorAll('.rating-cell');
                let hasVisibleRating = false;

                ratingCells.forEach(cell => {
                    // Tarkista kuuluuko solu kriitikolle jolla on oikea julkaisu
                    const headerIndex = cell.cellIndex - 1; // -1 koska movie-col
                    const header = table.querySelector(`thead th.rating-cell:nth-child(${cell.cellIndex + 1})`);
                    
                    if (header) {
                        const mediaSpan = header.querySelector('.critic-media');
                        const criticPublications = mediaSpan ? mediaSpan.textContent.trim().split(', ') : [];
                        const criticMatches = noFilter || publications.some(pub => criticPublications.includes(pub));
                        
                        if (criticMatches) {
                            const ratingLink = cell.querySelector('.rating-link');
                            const ratingStars = cell.querySelector('.rating-stars');
                            const noRating = cell.querySelector('.no-rating');
                            const isEmpty = noRating && noRating.textContent.trim() === '–';
                            
                            if ((ratingLink || ratingStars) || (noRating && !isEmpty)) {
                                hasVisibleRating = true;
                            }
                        }
                    }
                });

                if (noFilter) {
                    row.style.display = '';
                } else {
                    row.style.display = hasVisibleRating ? '' : 'none';
                }
            });

            // Käytä keskitettyä funktiota sarakkeiden piilotukseen
            if (typeof updateCriticColumnVisibility === 'function') {
                updateCriticColumnVisibility();
            }

            setTimeout(() => {
                if (window.removeFillerColumns) window.removeFillerColumns();
                if (window.addFillerColumns) window.addFillerColumns();
            }, 50);
        }
    }
}

// Initialize all click handlers
document.addEventListener('DOMContentLoaded', function () {
    initSorting();
    initMovieClickHandlers();
    initCriticClickHandlers();
    initMobileCriticClickHandlers();
    initRatingFilterClickHandlers();
    initPublicationFilterClickHandlers();
});
