// Kriitikon valinta - Main JavaScript
// =====================================

// Globaalit muuttujat
// ===================
let savedScrollLeft = 0;
let originalTableWidth = 0;
let originalVisibleColumns = 0;
let currentMovieOffset = 50; // Aloitetaan 50:stä, koska ensimmäiset 50 on jo ladattu Jinjalla
const movieLimit = 50;

// Utility Functions
// =================

/**
 * Näytä julistekuva elokuvasolussa
 */
function showPosterInCell(movieCell, posterUrl) {
    const existingPoster = movieCell.querySelector('.movie-poster');
    const existingLinks = movieCell.querySelectorAll('a');
    if (existingPoster) existingPoster.remove();
    existingLinks.forEach(link => link.remove());

    const movieTitle = movieCell.textContent.trim();
    movieCell.innerHTML = '';

    // Posterikuva
    const posterImg = document.createElement('img');
    posterImg.src = posterUrl;
    posterImg.alt = 'Elokuvan juliste';
    posterImg.className = 'movie-poster';
    movieCell.appendChild(posterImg);

    // Elokuvan nimi
    const titleSpan = document.createElement('div');
    titleSpan.textContent = movieTitle;
    titleSpan.className = 'movie-title';
    movieCell.appendChild(titleSpan);

    // Linkit
    const linksDiv = document.createElement('div');
    linksDiv.className = 'movie-links';

    // Nytleffaan
    const nytleffaanUrl = movieCell.dataset.nytleffaan;
    if (nytleffaanUrl) {
        const nytleffaanLink = document.createElement('a');
        nytleffaanLink.href = nytleffaanUrl;
        nytleffaanLink.target = '_blank';
        nytleffaanLink.innerHTML = '🎬 Osta liput';
        nytleffaanLink.className = 'movie-link nytleffaan-link';
        nytleffaanLink.title = 'Osta liput: nytleffaan.fi';
        linksDiv.appendChild(nytleffaanLink);
    }

    // Letterboxd
    const letterboxdUrl = movieCell.dataset.letterboxd;
    if (letterboxdUrl) {
        const letterboxdLink = document.createElement('a');
        letterboxdLink.href = letterboxdUrl;
        letterboxdLink.target = '_blank';
        letterboxdLink.textContent = '📽️ Letterboxd';
        letterboxdLink.className = 'movie-link letterboxd-link';
        letterboxdLink.title = 'Katso Letterboxd:ssä';
        linksDiv.appendChild(letterboxdLink);
    }

    movieCell.appendChild(linksDiv);
}

/**
 * Piilota julistekuva elokuvasolussa
 */
function hidePosterInCell(movieCell) {
    const poster = movieCell.querySelector('.movie-poster');
    if (poster) poster.remove();

    const nytleffaanLink = movieCell.querySelector('a[href*="nytleffaan"]');
    if (nytleffaanLink) nytleffaanLink.remove();

    const letterboxdLink = movieCell.querySelector('a[href*="letterboxd"]');
    if (letterboxdLink) letterboxdLink.remove();
}

/**
 * Palauta elokuvan nimi alkuperäiseen muotoon (poista linkit)
 */
function resetMovieCell(movieCell) {
    if (!movieCell) return;

    if (movieCell.__originalContent !== undefined) {
        movieCell.innerHTML = movieCell.__originalContent;
        return;
    }

    // Fallback: poista mahdolliset lisätyt linkkiblokit ja jätä muu sisältö koskemattomaksi
    const extraLinks = movieCell.querySelectorAll('.movie-links');
    extraLinks.forEach(el => el.remove());
}

/**
 * Lisää täytesarake joka venyy täyttämään tyhjän tilan
 */
function addFillerColumns() {
    const table = document.querySelector('table');
    const tableWrapper = document.querySelector('.table-wrapper');
    if (!table || !tableWrapper) return;

    const thead = table.querySelector('thead tr');
    const tbody = table.querySelector('tbody');

    if (thead.querySelector('.filler-column')) return;

    // Lisää täytesarake theadiin
    const fillerTh = document.createElement('th');
    fillerTh.className = 'filler-column';
    fillerTh.style.width = 'auto';
    fillerTh.style.backgroundColor = '#f8f9fa';
    fillerTh.innerHTML = '&nbsp;';
    thead.appendChild(fillerTh);

    // Lisää täytesarake jokaiselle näkyvissä olevalle riville
    tbody.querySelectorAll('tr').forEach(row => {
        if (row.style.display === 'none') return;

        const fillerTd = document.createElement('td');
        fillerTd.className = 'filler-column';
        fillerTd.style.backgroundColor = 'white';
        fillerTd.innerHTML = '&nbsp;';
        row.appendChild(fillerTd);
    });
}

/**
 * Poista täytesarakkeet
 */
function removeFillerColumns() {
    const fillers = document.querySelectorAll('.filler-column');
    fillers.forEach(filler => filler.remove());
}

// Column Management
// =================

/**
 * Järjestä kriitikkosarakkeet arvioiden mukaan
 */
function sortCriticColumnsByReviews() {
    const table = document.querySelector('table');
    if (!table) return;

    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;

    const criticRow = thead.querySelector('tr.critic-row');
    if (!criticRow) return;

    const criticHeaders = Array.from(criticRow.querySelectorAll('th:not(.movie-col)'));
    const allRows = Array.from(tbody.querySelectorAll('tr'));

    const orderedCritics = [];
    const seenCriticIndices = new Set();

    // Kerää kriitikot siinä järjestyksessä kun ne ensimmäisen kerran arvioivat elokuvan
    allRows.forEach(row => {
        if (row.style.display === 'none') return;

        const cells = row.querySelectorAll('td');

        criticHeaders.forEach((header, criticIndex) => {
            const columnIndex = criticIndex + 1;
            const cell = cells[columnIndex];

            if (seenCriticIndices.has(criticIndex)) return;

            if (cell) {
                const hasLink = cell.querySelector('a.rating-link');
                const ratingStars = cell.querySelector('.rating-stars');

                if (hasLink || ratingStars) {
                    orderedCritics.push({
                        header: header,
                        originalIndex: criticIndex,
                        columnIndex: columnIndex
                    });
                    seenCriticIndices.add(criticIndex);
                }
            }
        });
    });

    // Lisää loput kriitikot loppuun
    criticHeaders.forEach((header, criticIndex) => {
        if (!seenCriticIndices.has(criticIndex)) {
            orderedCritics.push({
                header: header,
                originalIndex: criticIndex,
                columnIndex: criticIndex + 1
            });
        }
    });

    // Tallenna kaikki solut
    const rowCells = allRows.map(row => {
        return Array.from(row.querySelectorAll('td:not(.movie-col)'));
    });

    // Tyhjennä headerit
    criticHeaders.forEach(h => h.remove());

    // Lisää headerit uudessa järjestyksessä
    orderedCritics.forEach(item => {
        criticRow.appendChild(item.header);
    });

    // Järjestä rivien solut samassa järjestyksessä
    allRows.forEach((row, rowIndex) => {
        const cells = rowCells[rowIndex];
        cells.forEach(c => c.remove());

        orderedCritics.forEach(item => {
            const cell = cells[item.originalIndex];
            if (cell) row.appendChild(cell);
        });
    });
}

/**
 * Päivitä kriitikkosarakkeiden näkyvyys
 */
function updateCriticColumnVisibility() {
    const table = document.querySelector('table');
    if (!table) return;

    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    if (!thead || !tbody) return;

    const criticRow = thead.querySelector('tr.critic-row');
    if (!criticRow) return;

    const criticHeaders = criticRow.querySelectorAll('th:not(.movie-col)');
    const visibleRows = Array.from(tbody.querySelectorAll('tr')).filter(row => {
        return row.style.display !== 'none';
    });

    const starSlider = document.getElementById('star-filter-slider');
    const activeStarFilter = starSlider ? parseInt(starSlider.value) : 1;
    const hasActiveStarFilter = activeStarFilter > 1;

    // Käy läpi jokainen kriitikko (sarake)
    criticHeaders.forEach((header, index) => {
        const columnIndex = index + 1;
        const criticId = header.dataset.criticId;
        let hasVisibleReview = false;

        // Check favorites filter
        const favoritesActive = window.isFavoritesFilterActive && window.isFavoritesFilterActive();
        const isFav = window.isFavoriteCritic && window.isFavoriteCritic(criticId);

        if (favoritesActive && !isFav) {
            // Jos suosikkifiltteri päällä ja kriitikko ei ole suosikki, piilota heti
            hasVisibleReview = false;
        } else {
            // Muuten tarkista onko arvosteluja
            visibleRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const cell = cells[columnIndex];

                if (cell) {
                    const hasLink = cell.querySelector('a.rating-link');
                    const ratingStars = cell.querySelector('.rating-stars');
                    const noRating = cell.querySelector('.no-rating');
                    const isEmpty = noRating && noRating.textContent.trim() === '–';

                    if ((hasLink || ratingStars) || (noRating && !isEmpty)) {
                        if (hasActiveStarFilter && ratingStars) {
                            const starCount = (ratingStars.textContent.match(/★/g) || []).length;
                            if (starCount >= activeStarFilter) {
                                hasVisibleReview = true;
                            }
                        } else if (!hasActiveStarFilter) {
                            hasVisibleReview = true;
                        }
                    }
                }
            });
        }

        // Piilota tai näytä sarake
        if (hasVisibleReview) {
            header.classList.remove('filter-hidden');
            tbody.querySelectorAll('tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[columnIndex]) {
                    cells[columnIndex].classList.remove('filter-hidden');
                }
            });
        } else {
            header.classList.add('filter-hidden');
            tbody.querySelectorAll('tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[columnIndex]) {
                    cells[columnIndex].classList.add('filter-hidden');
                }
            });
        }
    });

    // Päivitä "joka toinen" -väritys VAIN näkyville sarakkeille
    const visibleHeaders = Array.from(criticHeaders).filter(header =>
        !header.classList.contains('filter-hidden') && header.style.display !== 'none'
    );

    // Poista KAIKKI väritysluokat ensin
    criticHeaders.forEach(header => {
        header.classList.remove('even-column', 'odd-column');
    });
    tbody.querySelectorAll('tr').forEach(row => {
        row.querySelectorAll('td.rating-cell').forEach(cell => {
            cell.classList.remove('even-column', 'odd-column');
        });
    });

    // Lisää väritysluokat VAIN näkyville sarakkeille
    visibleHeaders.forEach((header, visibleIndex) => {
        const columnClass = visibleIndex % 2 === 0 ? 'even-column' : 'odd-column';
        header.classList.add(columnClass);

        const columnIndex = Array.from(criticHeaders).indexOf(header) + 1;
        tbody.querySelectorAll('tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells[columnIndex] && !cells[columnIndex].classList.contains('filter-hidden')) {
                cells[columnIndex].classList.add(columnClass);
            }
        });
    });

    // Päivitä rivien näkyvyys (piilota rivit joilla ei ole näkyviä arvioita)
    updateRowVisibility();
}

/**
 * Päivitä rivien näkyvyys visuaalisten sarakkeiden perusteella
 * Piilottaa rivit, joilla ei ole yhtään näkyvää arvostelua aktiivisissa sarakkeissa
 */
function updateRowVisibility() {
    const table = document.querySelector('table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const allRows = tbody.querySelectorAll('tr:not(.poster-row)');

    // Hae kaikki näkyvät kriitikkosarakkeet
    const headerRow = table.querySelector('thead tr.critic-row');
    if (!headerRow) return;

    const allHeaders = Array.from(headerRow.querySelectorAll('th.rating-cell'));
    const visibleColumnIndices = [];

    allHeaders.forEach((header, index) => {
        if (header.style.display !== 'none' && !header.classList.contains('filter-hidden')) {
            visibleColumnIndices.push(index + 1); // +1 because index 0 is movie title
        }
    });

    allRows.forEach(row => {
        // Jos rivi on jo piilotettu muista syistä (esim. tekstihaku, tähdet), älä koske
        // Mutta meidän pitää erottaa "ei arvosteluja" -piilotus "filtteri"-piilotuksesta logic chainissa.
        // Tässä oletamme, että tämä ajetaan viimeisenä.

        // Emme koske riveihin, jotka on piilotettu review-count tai star filtterillä
        if (row.dataset.reviewCountFiltered === 'true' || row.dataset.starFiltered === 'true') {
            return;
        }

        let hasVisibleReview = false;
        const cells = row.querySelectorAll('td');

        for (const colIndex of visibleColumnIndices) {
            const cell = cells[colIndex];
            if (cell) {
                const hasLink = cell.querySelector('a.rating-link');
                const ratingStars = cell.querySelector('.rating-stars');
                const noRating = cell.querySelector('.no-rating');
                const isEmpty = noRating && noRating.textContent.trim() === '–';

                if ((hasLink || ratingStars) || (noRating && !isEmpty)) {
                    hasVisibleReview = true;
                    break;
                }
            }
        }

        if (hasVisibleReview) {
            // Do not unhide if row is specifically dimmed by interaction
            if (!row.classList.contains('dimmed')) {
                row.style.display = '';
            }
        } else {
            row.style.display = 'none';
        }
    });

    // Päivitä myös sticky scrollbar
    const stickyScrollbar = document.querySelector('.sticky-scrollbar-container');
    if (stickyScrollbar && getComputedStyle(stickyScrollbar).display !== 'none') {
        // Trigger resize event implies scrollbar update
        window.dispatchEvent(new Event('resize'));
    }
}

// Lazy Loading
// ============

/**
 * Lataa lisää elokuvia ja liittää ne taulukkoon ja kortteihin.
 */
async function loadMoreMovies() {
    const loadMoreButton = document.getElementById('load-more-button');
    if (!loadMoreButton) return;

    loadMoreButton.disabled = true;
    const originalText = loadMoreButton.textContent;
    loadMoreButton.textContent = 'Ladataan...';

    try {
        const response = await fetch(`/api/movies?offset=${currentMovieOffset}&limit=${movieLimit}`);
        const data = await response.json();

        if (data.movies_html) {
            const desktopTbody = document.querySelector('#review-container-desktop tbody');
            const mobileCardsContainer = document.querySelector('.mobile-cards');

            if (desktopTbody) {
                // Lisää HTML-pätkä
                desktopTbody.insertAdjacentHTML('beforeend', data.movies_html);
            }

            if (mobileCardsContainer) {
                // Lisää HTML-pätkä
                mobileCardsContainer.insertAdjacentHTML('beforeend', data.cards_html);
            }

            // Päivitä offset
            currentMovieOffset += data.count;

            // Alusta uudet elementit (click handlerit jne)
            // Huom: meidän täytyy re-alustaa kaikki, koska jotkut funktiot
            // skannaavat koko DOM:in uudelleen.
            if (typeof initMovieClickHandlers === 'function') initMovieClickHandlers();
            if (typeof initMobileCriticClickHandlers === 'function') initMobileCriticClickHandlers();
            if (typeof initRatingFilterClickHandlers === 'function') initRatingFilterClickHandlers();
            if (typeof initReviewCountFilter === 'function') initReviewCountFilter();
            if (typeof initStarFilter === 'function') initStarFilter();
            if (typeof initFavoriteFilter === 'function') initFavoriteFilter();
            
            // Järjestä uudelleen jos tarpeen
            if (typeof updateCriticColumnVisibility === 'function') updateCriticColumnVisibility();
        }

        // Piilota nappi jos kaikki on ladattu
        if (currentMovieOffset >= data.total) {
            loadMoreButton.parentElement.style.display = 'none';
        }

    } catch (error) {
        console.error('Virhe elokuvien latauksessa:', error);
        alert('Lisää elokuvia ei voitu ladata. Yritä uudelleen.');
    } finally {
        loadMoreButton.disabled = false;
        loadMoreButton.textContent = originalText;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const loadMoreButton = document.getElementById('load-more-button');
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', loadMoreMovies);
        
        // Tarkista heti pitääkö nappi piilottaa (jos alle 50 elokuvaa yhteensä)
        const totalMoviesText = document.querySelector('.header-stat:nth-child(2)')?.textContent;
        if (totalMoviesText) {
            const total = parseInt(totalMoviesText);
            if (!isNaN(total) && total <= 50) {
                loadMoreButton.parentElement.style.display = 'none';
            }
        }
    }
});


// Export global functions
// =======================
window.sortCriticColumnsByReviews = sortCriticColumnsByReviews;
window.updateCriticColumnVisibility = updateCriticColumnVisibility;
window.updateRowVisibility = updateRowVisibility;
window.showPosterInCell = showPosterInCell;
window.hidePosterInCell = hidePosterInCell;
window.resetMovieCell = resetMovieCell;
window.addFillerColumns = addFillerColumns;
window.removeFillerColumns = removeFillerColumns;
