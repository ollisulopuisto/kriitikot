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

        movieCell.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            const clickedRow = movieCell.parentElement;
            const isAlreadySelected = clickedRow.dataset.filtered === 'true';
            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();

            if (isAlreadySelected) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }

            // Jos jokin muu filtteri on päällä, nollataan se ensin mutta jatketaan korostukseen
            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
            }

            // Poista vanhat poster-rivit
            tbody.querySelectorAll('.poster-row').forEach(pr => pr.remove());

            // Tallenna alkuperäinen taulukon leveys
            if (!window.originalTableWidth) {
                window.originalTableWidth = table.offsetWidth;
            }

            // Merkitse rivi ja solu valituksi ENNEN muiden päivitysten ajoa
            clickedRow.dataset.filtered = 'true';
            movieCell.classList.add('selected');

            // Skrollaa ikkunaa niin, että taulukon alku on näkyvissä headerin alla
            const tableWrapper = document.querySelector('.table-wrapper');
            const desktopFilters = document.querySelector('.desktop-filters');

            if (tableWrapper && desktopFilters) {
                setTimeout(() => {
                    const filtersHeight = desktopFilters.offsetHeight;
                    const tableTop = tableWrapper.getBoundingClientRect().top + window.pageYOffset;
                    // Skrollataan niin että table-wrapper on juuri fassettien alla
                    const scrollToY = tableTop - filtersHeight;

                    window.scrollTo({
                        top: scrollToY,
                        behavior: 'auto' // Use auto for reliability during layout changes
                    });
                }, 50);
            }

            // Päivitä näkyvyys välittömästi (tämä hoitaa sarakkeiden ja muiden rivien piilottamisen)
            if (typeof updateCriticColumnVisibility === 'function') {
                updateCriticColumnVisibility();
            }

            // Päivitä sticky header jos se on olemassa
            if (window.refreshStickyHeader) {
                window.refreshStickyHeader();
            }
            // Lisää linkit elokuvan nimen / laskurin alapuolelle koskematta alkuperäiseen rakenteeseen
            const nytleffaanUrl = movieCell.dataset.nytleffaan;
            const letterboxdUrl = movieCell.dataset.letterboxd;
            
            // Tarkista onko linkit jo olemassa (SSR tai aiempi klikkaus)
            const existingLinks = movieCell.querySelector('.movie-links') || 
                                 (movieCell.querySelector('.nytleffaan-link') && movieCell.querySelector('.letterboxd-link'));

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

                clickedRow.parentNode.insertBefore(posterRow, clickedRow.nextSibling);
            }

            if (window.addFillerColumns) window.addFillerColumns();
            if (window.showResetButton) window.showResetButton();
        });
        movieCell.dataset.initialized = 'true';
    });
}

/**
 * Suodata näkymä näyttämään vain yhden kriitikon arvostelut
 */
window.filterByCritic = function(criticIdOrHeader) {
    let criticId;
    let criticHeader;
    
    if (typeof criticIdOrHeader === 'string') {
        criticId = criticIdOrHeader;
    } else if (criticIdOrHeader && criticIdOrHeader.dataset && criticIdOrHeader.dataset.criticId) {
        criticId = criticIdOrHeader.dataset.criticId;
        criticHeader = criticIdOrHeader;
    } else {
        return;
    }

    console.log('Filtering by critic:', criticId);

    const table = document.querySelector('table');
    const allCards = document.querySelectorAll('.movie-card');

    if (table) {
        const tbody = table.querySelector('tbody');
        const criticHeaders = Array.from(table.querySelectorAll('thead th.rating-cell'));

        if (!criticHeader) {
            criticHeader = criticHeaders.find(h => h.dataset.criticId === criticId);
        }

        // Poista aiemmat poster-rivit sekaannusten välttämiseksi
        tbody.querySelectorAll('.poster-row').forEach(row => row.remove());

        // Nollaa table-wrapper skrollaus vasempaan reunaan
        const tableWrapper = document.querySelector('.table-wrapper');
        if (tableWrapper) {
            tableWrapper.scrollLeft = 0;
        }

        // Aseta filtered-tila vain valitulle otsikolle
        criticHeaders.forEach(header => {
            if (header === criticHeader) {
                header.dataset.filtered = 'true';
                header.classList.add('selected');
            } else {
                delete header.dataset.filtered;
                header.classList.remove('selected');
            }
        });

        if (typeof updateCriticColumnVisibility === 'function') {
            updateCriticColumnVisibility();
        }
    }

    // Päivitä Mobiili-näkymä jos se on käytössä
    if (allCards.length > 0) {
        allCards.forEach(card => {
            const cardHasSelectedCritic = Array.from(card.querySelectorAll('.review-item'))
                .some(item => item.dataset.critic === criticId);

            if (!cardHasSelectedCritic) {
                card.style.display = 'none';
            } else {
                card.style.display = '';
                card.querySelectorAll('.review-item').forEach(item => {
                    item.style.display = (item.dataset.critic === criticId) ? '' : 'none';
                });
            }
        });
        
        const allReviewItems = document.querySelectorAll('.review-item');
        allReviewItems.forEach(item => {
            const area = item.querySelector('.review-critic');
            const name = item.querySelector('.review-critic-name');
            if (area && name) {
                if (item.dataset.critic === criticId) {
                    name.classList.add('selected');
                    area.dataset.filtered = 'true';
                } else {
                    name.classList.remove('selected');
                    delete area.dataset.filtered;
                }
            }
        });

        const criticFilterValue = document.getElementById('critic-filter-value-mobile');
        if (criticFilterValue) {
            // Etsi kriitikon oikea nimi (display name) joko mobiili-DOM:sta tai pöytäkone-DOM:sta
            let displayName = criticId;
            const selectedReview = Array.from(allReviewItems).find(item => item.dataset.critic === criticId);
            if (selectedReview) {
                const nameEl = selectedReview.querySelector('.review-critic-name');
                if (nameEl && nameEl.textContent) displayName = nameEl.textContent.trim();
            } else if (criticHeader) {
                const nameEl = criticHeader.querySelector('.critic-name');
                if (nameEl && nameEl.textContent) displayName = nameEl.textContent.trim();
            }
            criticFilterValue.textContent = displayName;
        }
    }

    // Näytä nollauspainike
    if (window.showResetButton) window.showResetButton();

    // Päivitä sticky header
    if (window.refreshStickyHeader) {
        window.refreshStickyHeader();
    }
    
    // Hallitse täytesarakkeita
    if (window.removeFillerColumns) window.removeFillerColumns();
    if (window.addFillerColumns) window.addFillerColumns();
};

/**
 * Kriitikon nimi click handler (Suodatus)
 */
function initCriticClickHandlers() {
    const table = document.querySelector('table');
    if (!table) return;

    const criticHeaders = table.querySelectorAll('thead th.rating-cell');

    criticHeaders.forEach((criticHeader) => {
        // Alusta klikattavaksi
        criticHeader.style.cursor = 'pointer';
        criticHeader.title = 'Klikkaa näyttääksesi vain tämän kriitikon arvostelut';

        // Käytä nimettyä funktiota delegoinnin helpottamiseksi
        if (!criticHeader.dataset.clickInitialized) {
            criticHeader.addEventListener('click', function () {
                window.filterByCritic(this);
            });
            criticHeader.dataset.clickInitialized = 'true';
        }
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
            if (window.filterByCritic) {
                window.filterByCritic(selectedCritic);
            }
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
    
    // Alusta tilat
    publicationFilters.forEach(pubFilter => {
        if (pubFilter.dataset.initialized) return;
        
        pubFilter.addEventListener('click', function (e) {
            e.preventDefault();
            console.log('Media filter clicked:', this.dataset.publication);

            const selectedPub = this.dataset.publication;
            const isCurrentlyActive = this.classList.contains('active');
            
            // Hae KAIKKI saman julkaisun painikkeet (desktop + mobile)
            const samePubButtons = document.querySelectorAll(`.filter-publication[data-publication="${selectedPub}"]`);
            console.log(`Found ${samePubButtons.length} buttons for ${selectedPub}`);
            
            if (isCurrentlyActive) {
                samePubButtons.forEach(btn => btn.classList.remove('active'));
            } else {
                samePubButtons.forEach(btn => btn.classList.add('active'));
            }

            // Kerää kaikki aktiiviset julkaisut DOM:sta (koska ne on nyt synkattu)
            const activePubButtons = document.querySelectorAll('.filter-publication.active');
            const activePubs = Array.from(new Set(Array.from(activePubButtons).map(btn => btn.dataset.publication)));
            console.log('Active publications:', activePubs);

            applyPublicationFilter(activePubs);

            if (activePubs.length > 0) {
                if (window.showResetButton) window.showResetButton();
            }
        });
        pubFilter.dataset.initialized = 'true';
    });

    function applyPublicationFilter(publications) {
        console.log('Applying publication filter for:', publications);
        const allCards = document.querySelectorAll('.movie-card');
        const table = document.querySelector('table');
        const noFilter = publications.length === 0;
        console.log(`noFilter: ${noFilter}, allCards: ${allCards.length}, table: ${!!table}`);

        // Mobile cards
        allCards.forEach(card => {
            const cardReviews = card.querySelectorAll('.review-item');
            let hasMatchingReview = false;

            cardReviews.forEach(item => {
                if (noFilter) {
                    item.style.display = '';
                    hasMatchingReview = true;
                } else {
                    const mediaElement = item.querySelector('.review-media');
                    const mediaText = mediaElement ? mediaElement.textContent.trim().toUpperCase() : '';
                    
                    // Match if any of the active publications is contained in mediaText
                    const matches = publications.some(pub => mediaText.includes(pub));
                    
                    if (matches) {
                        item.style.display = '';
                        hasMatchingReview = true;
                    } else {
                        item.style.display = 'none';
                    }
                }
            });

            // Älä näytä korttia jos se on jo piilotettu muun suodattimen takia
            // (paitsi jos olemme juuri poistamassa tätä filtteriä)
            if (noFilter) {
                // Tässä pitäisi periaatteessa ajaa kaikki muut suodattimet uusiksi
                // mutta toistaiseksi vain näytetään
                card.style.display = '';
            } else {
                card.style.display = hasMatchingReview ? '' : 'none';
            }
        });

        // Desktop table
        if (table) {
            const tbody = table.querySelector('tbody');
            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');
            const thead = table.querySelector('thead');
            const criticHeaders = Array.from(thead.querySelectorAll('th.rating-cell'));

            allRows.forEach(row => {
                const ratingCells = row.querySelectorAll('.rating-cell');
                let hasVisibleRating = false;

                ratingCells.forEach(cell => {
                    const cellIndex = cell.cellIndex;
                    // Etsi vastaava header sarakkeen cellIndexillä
                    const header = criticHeaders.find(h => h.cellIndex === cellIndex);
                    
                    if (header) {
                        const mediaSpan = header.querySelector('.critic-media');
                        const criticPublications = mediaSpan ? mediaSpan.textContent.trim().split(', ') : [];
                        const criticMatches = noFilter || publications.some(pub => criticPublications.includes(pub));
                        
                        // Piilota/näytä yksittäiset arvostelut solun sisällä
                        const cellReviews = cell.querySelectorAll('[data-publication]');
                        let cellHasVisibleReview = false;
                        
                        cellReviews.forEach(rev => {
                            const revPub = (rev.dataset.publication || '').toUpperCase();
                            // Match if revPub matches any of our active publications
                            const matchesRev = noFilter || publications.some(pub => revPub.includes(pub.toUpperCase()));
                            
                            if (matchesRev) {
                                rev.style.display = '';
                                if (rev.tagName !== 'BR') cellHasVisibleReview = true;
                            } else {
                                rev.style.display = 'none';
                            }
                        });

                        if (criticMatches && (noFilter || cellHasVisibleReview)) {
                            hasVisibleRating = true;
                        }
                    }
                });

                if (noFilter) {
                    // Jos filtteri poistetaan, palauta näkyvyys jos se ei ole jo piilotettu muualta
                    // (Tämä on vaikeaa koska ei ole keskitettyä statea, mutta yritetään)
                    const isStarFiltered = row.dataset.starFiltered === 'true';
                    const isCountFiltered = row.dataset.reviewCountFiltered === 'true';
                    if (!isStarFiltered && !isCountFiltered) {
                        row.style.display = '';
                    }
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
function initAllInteractions() {
    initSorting();
    initMovieClickHandlers();
    initCriticClickHandlers();
    initMobileCriticClickHandlers();
    initRatingFilterClickHandlers();
    initPublicationFilterClickHandlers();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllInteractions);
} else {
    initAllInteractions();
}

// Export functions to window
window.initMovieClickHandlers = initMovieClickHandlers;
window.initCriticClickHandlers = initCriticClickHandlers;
window.initMobileCriticClickHandlers = initMobileCriticClickHandlers;
window.initRatingFilterClickHandlers = initRatingFilterClickHandlers;
window.initPublicationFilterClickHandlers = initPublicationFilterClickHandlers;
