// Kriitikon valinta - Main JavaScript
// =====================================

// Globaalit muuttujat
// ===================
let savedScrollLeft = 0;
let originalTableWidth = 0;
let originalVisibleColumns = 0;
let currentMovieOffset = 30; // Aloitetaan 30:stä, koska ensimmäiset 30 on jo ladattu Jinjalla
const movieLimit = 30;
let allGroupedReviews = {}; // Tähän ladataan kaikki arvostelut JSONista
let allCritics = []; // Kaikki kriitikot, tarvitaan renderöintiin (id ja name)
let allCriticsMap = {}; // Map kriitikoista {id: critic_object}
let allPublicationMap = {}; // Map julkaisuista {short_name: publication_object}


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
            const cell = rowCells[rowIndex][item.originalIndex];
            if (cell) row.appendChild(cell);
        });
    });

    // Päivitä sticky header
    document.dispatchEvent(new CustomEvent('table-sorted'));
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

    const criticHeaders = Array.from(criticRow.querySelectorAll('th.rating-cell'));
    const visibleRows = Array.from(tbody.querySelectorAll('tr:not(.poster-row)')).filter(row => {
        return row.style.display !== 'none';
    });

    const starSlider = document.getElementById('star-filter-slider');
    const activeStarFilter = starSlider ? parseInt(starSlider.value) : 1;
    const hasActiveStarFilter = activeStarFilter > 1;

    // Tarkista onko julkaisufiltteri aktiivinen
    const activePubButtons = document.querySelectorAll('.filter-publication.selected, .media-filter-btn.active');
    const activePubs = Array.from(activePubButtons).map(btn => btn.dataset.publication);
    const hasActivePubFilter = activePubs.length > 0;

    // Käy läpi jokainen kriitikko (sarake)
    criticHeaders.forEach((header) => {
        const criticId = header.dataset.criticId;
        const criticName = header.querySelector('.critic-name') ? header.querySelector('.critic-name').textContent.trim() : criticId;
        const cellIndex = header.cellIndex;
        if (cellIndex === -1) return;
        
        let hasVisibleReview = false;

        // Check favorites filter
        const favoritesActive = window.isFavoritesFilterActive && window.isFavoritesFilterActive();
        const isFav = window.isFavoriteCritic && window.isFavoriteCritic(criticId);

        if (favoritesActive && !isFav) {
            hasVisibleReview = false;
        } else {
            // Tarkista julkaisufiltteri tälle kriitikolle
            if (hasActivePubFilter) {
                const mediaSpan = header.querySelector('.critic-media');
                const criticPubs = mediaSpan ? mediaSpan.textContent.trim().split(', ') : [];
                const matchesPub = activePubs.some(pub => criticPubs.includes(pub));
                if (!matchesPub) {
                    hasVisibleReview = false;
                } else {
                    hasVisibleReview = checkRowsForReview(visibleRows, cellIndex, hasActiveStarFilter, activeStarFilter, criticName);
                }
            } else {
                hasVisibleReview = checkRowsForReview(visibleRows, cellIndex, hasActiveStarFilter, activeStarFilter, criticName);
            }
        }

        // Piilota tai näytä sarake
        const rowsToUpdate = Array.from(table.rows);
        if (hasVisibleReview) {
            header.classList.remove('filter-hidden');
            rowsToUpdate.forEach(row => {
                const cell = row.cells[cellIndex];
                if (cell) cell.classList.remove('filter-hidden');
            });
        } else {
            // console.log(`🙈 Hiding column for ${criticName} (cellIndex: ${cellIndex})`);
            header.classList.add('filter-hidden');
            rowsToUpdate.forEach(row => {
                const cell = row.cells[cellIndex];
                if (cell) cell.classList.add('filter-hidden');
            });
        }
    });

    /**
     * Apufunktio: Tarkista löytyykö sarakkeesta näkyviä arvioita
     */
    function checkRowsForReview(rows, cellIndex, hasStarFilter, starLimit, criticName) {
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const cell = row.cells[cellIndex];
            if (!cell) continue;

            const ratingStars = cell.querySelectorAll('.rating-stars');
            const hasLink = cell.querySelector('a.rating-link');
            const noRating = cell.querySelector('.no-rating');
            const isEmpty = noRating && noRating.textContent.trim() === '–';

            // Jos sarakkeessa on jotain sisältöä
            if (hasLink || ratingStars.length > 0 || (noRating && !isEmpty)) {
                if (hasStarFilter) {
                    // Jos tähtifiltteri on päällä, sarakkeen on oltava näkyvissä 
                    // vain jos se sisältää vähintään yhden kriteerin täyttävän arvion.
                    if (ratingStars.length > 0) {
                        for (const starSpan of ratingStars) {
                            const starCount = (starSpan.textContent.match(/★/g) || []).length;
                            if (starCount >= starLimit) {
                                return true;
                            }
                        }
                    }
                } else {
                    // Ei tähtifiltteriä, mikä tahansa sisältö riittää
                    return true;
                }
            }
        }
        return false;
    }

    // Päivitä "joka toinen" -väritys VAIN näkyville sarakkeille
    const visibleHeaders = criticHeaders.filter(header =>
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

        // Jos rivi on valittu klikkaamalla elokuvan nimeä, pidetään se aina näkyvissä
        if (row.dataset.filtered === 'true') {
            row.style.display = '';
            row.classList.remove('dimmed');
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

function createReviewPill(review) {
    let tooltipText = review.review_text ? review.review_text.substring(0, 200) : 'Lue arvostelu';
    let starsHtml = '★'.repeat(review.rating_stars);
    let publicationName = allPublicationMap[review.source_publication]?.name || review.source_publication; // Get full name
    
    if (review.source_url) {
        return `
            <a href="${review.source_url}"
                class="rating-link rating-pill stars-${review.rating_stars}" target="_blank"
                title="${publicationName}: ${tooltipText}...">
                <span class="rating-stars">${starsHtml}</span>
            </a>
        `;
    } else {
        return `
            <span class="rating-pill stars-${review.rating_stars}">
                <span class="rating-stars">${starsHtml}</span>
            </span>
        `;
    }
}


/**
 * Renderöi elokuvarivin tai kortin
 */
function renderMovie(movieTitle, criticsReviewsDict) {
    // Collect movie meta info (poster, letterboxd, nytleffaan, review counts) from the global data structures
    const posterUrl = window.poster_urls[movieTitle] || '';
    const letterboxdUrl = window.letterboxd_urls[movieTitle] || '';
    const nytleffaanUrl = window.nytleffaan_urls[movieTitle] || '';
    const movieReviewCount = window.movie_review_counts[movieTitle];

    // Desktop row
    let desktopHtml = `
        <tr>
            <td class="movie-col" data-poster="${posterUrl}"
                data-letterboxd="${letterboxdUrl}"
                data-nytleffaan="${nytleffaanUrl}">
                <div class="movie-title-main">${movieTitle}</div>
                ${movieReviewCount ? `<div class="movie-review-count">🎬 ${movieReviewCount}</div>` : ''}
            </td>
    `;
    // Populate with critics from allCritics (global, ordered list)
    allCritics.forEach(critic => {
        desktopHtml += `<td class="rating-cell">`;
        if (criticsReviewsDict[critic.name]) {
            criticsReviewsDict[critic.name].forEach((review, index) => {
                if (review.rating_stars) {
                    desktopHtml += createReviewPill(review);
                }
                if (index < criticsReviewsDict[critic.name].length - 1) {
                    desktopHtml += '<br>';
                }
            });
        }
        desktopHtml += `</td>`;
    });
    desktopHtml += `</tr>`;

    // Mobile card
    let mobileHtml = `
        <div class="movie-card" data-movie="${movieTitle}">
            <div class="movie-card-header">
                <div class="movie-card-title-row">
                    <div class="movie-card-title">${movieTitle}</div>
                    ${movieReviewCount ? `<div class="movie-card-review-count">🎬 ${movieReviewCount}</div>` : ''}
                    ${posterUrl ? `<img class="movie-card-poster" src="${posterUrl}" alt="Poster" />` : ''}
                </div>
            </div>
            <div class="movie-card-body">
    `;
    // Populate with critics from allCritics (global, ordered list)
    allCritics.forEach(critic => {
        if (criticsReviewsDict[critic.name]) {
            criticsReviewsDict[critic.name].forEach(review => {
                mobileHtml += `
                    <div class="review-item" data-critic="${critic.id}"
                        data-publication="${review.source_publication}">
                        <div class="review-critic">
                            <div class="review-critic-top">
                                <span class="review-critic-name">${critic.name}</span>
                            </div>
                            <div class="review-media">${review.source_publication.toUpperCase()}</div>
                        </div>
                        <div class="review-rating">
                            ${review.rating_stars ? createReviewPill(review) : ''}
                        </div>
                    </div>
                `;
            });
        }
    });
    if (nytleffaanUrl || letterboxdUrl) {
        mobileHtml += `<div class="movie-card-links">`;
        if (nytleffaanUrl) {
            mobileHtml += `<a href="${nytleffaanUrl}" target="_blank" class="movie-link nytleffaan-link">Osta liput</a>`;
        }
        if (letterboxdUrl) {
            mobileHtml += `<a href="${letterboxdUrl}" target="_blank" class="movie-link letterboxd-link">Letterboxd</a>`;
        }
        mobileHtml += `</div>`;
    }
    mobileHtml += `</div></div>`;

    return { desktop: desktopHtml, mobile: mobileHtml };
}


function loadMoreMovies() {
    const loadMoreButton = document.getElementById('load-more-button');
    if (!loadMoreButton) return;

    loadMoreButton.disabled = true;
    const originalText = loadMoreButton.textContent;
    loadMoreButton.textContent = 'Ladataan...';

    const desktopTbody = document.querySelector('#review-container-desktop tbody');
    const mobileCardsContainer = document.querySelector('.mobile-cards');

    if (!desktopTbody || !mobileCardsContainer) {
        console.error('Review containers not found');
        loadMoreButton.parentElement.style.display = 'none';
        return;
    }

    const movieTitles = Object.keys(allGroupedReviews);
    const moviesToRender = movieTitles.slice(currentMovieOffset, currentMovieOffset + movieLimit);

    if (moviesToRender.length === 0) {
        loadMoreButton.parentElement.style.display = 'none';
        loadMoreButton.disabled = false;
        loadMoreButton.textContent = originalText;
        return;
    }

    moviesToRender.forEach(movieTitle => {
        const criticsReviewsDict = allGroupedReviews[movieTitle];
        const { desktop, mobile } = renderMovie(movieTitle, criticsReviewsDict);
        
        desktopTbody.insertAdjacentHTML('beforeend', desktop);
        mobileCardsContainer.insertAdjacentHTML('beforeend', mobile);
    });
    
    currentMovieOffset += moviesToRender.length;

    if (currentMovieOffset >= movieTitles.length) {
        loadMoreButton.parentElement.style.display = 'none';
    } else {
        loadMoreButton.parentElement.style.display = 'block';
    }

    // Re-initialize event handlers for newly added elements
    if (typeof initMovieClickHandlers === 'function') initMovieClickHandlers();
    if (typeof initMobileCriticClickHandlers === 'function') initMobileCriticClickHandlers();
    if (typeof initRatingFilterClickHandlers === 'function') initRatingFilterClickHandlers();
    if (typeof initReviewCountFilter === 'function') initReviewCountFilter();
    if (typeof initStarFilter === 'function') initStarFilter();
    if (typeof initResetButton === 'function') initResetButton();
    if (typeof initFavoriteFilter === 'function') initFavoriteFilter();
    
    if (typeof updateCriticColumnVisibility === 'function') updateCriticColumnVisibility();
    
    loadMoreButton.disabled = false;
    loadMoreButton.textContent = originalText;
}


document.addEventListener('DOMContentLoaded', () => {
    // Lataa kaikki arvostelut JSONista
    const reviewsDataElement = document.getElementById('all-reviews-data');
    if (reviewsDataElement) {
        try {
            allGroupedReviews = JSON.parse(reviewsDataElement.textContent);
            
            // Haetaan kriitikkojen tiedot taulukon headerista
            const criticHeaders = document.querySelectorAll('thead th.rating-cell');
            allCritics = Array.from(criticHeaders).map(th => ({
                id: th.dataset.criticId,
                name: th.querySelector('.critic-name').textContent
            }));
            allCritics.forEach(c => allCriticsMap[c.id] = c);

            // Haetaan julkaisujen tiedot (oletetaan, että ne ovat jo renderöity)
            // tai haetaan dynaamisesti tarvittaessa
            // Placeholder, tässä vaiheessa ei ole suoraa tapaa JSONissa saada julkaisun koko nimeä
            // joten käytetään short_name.toUpperCase() tarvittaessa.
            // allPublicationMap will be populated with actual names if available elsewhere,
            // otherwise use short_name.
            document.querySelectorAll('.media-filter-btn').forEach(btn => {
                const short_name = btn.dataset.publication.toLowerCase();
                const name = btn.textContent.trim();
                allPublicationMap[short_name] = { short_name: short_name, name: name };
            });


            // Movie meta info (poster, letterboxd, nytleffaan, review counts)
            // Initial items are rendered by Jinja, so we can extract these from there.
            // These objects will be populated with actual data from allGroupedReviews during rendering
            window.nytleffaan_urls = {};
            window.poster_urls = {};
            window.letterboxd_urls = {};
            window.movie_review_counts = {};
            
            // Extract from initial Jinja-rendered movie cells
            document.querySelectorAll('#review-container-desktop tbody tr .movie-col').forEach(movieCol => {
                const movieTitle = movieCol.querySelector('.movie-title-main').textContent;
                window.nytleffaan_urls[movieTitle] = movieCol.dataset.nytleffaan;
                window.poster_urls[movieTitle] = movieCol.dataset.poster;
                window.letterboxd_urls[movieTitle] = movieCol.dataset.letterboxd;
                const countElem = movieCol.querySelector('.movie-review-count');
                if (countElem) {
                    window.movie_review_counts[movieTitle] = parseInt(countElem.textContent.replace('🎬 ', ''));
                }
            });

            // No need to clear Jinja-rendered content, as we want to keep it.
            // Initial render call should start from currentMovieOffset (which is 50)
            loadMoreMovies();

        } catch (e) {
            console.error('Error parsing all-reviews-data:', e);
            // Piilota lataa lisää -nappi jos dataa ei voi ladata
            const loadMoreButton = document.getElementById('load-more-button');
            if (loadMoreButton) {
                loadMoreButton.parentElement.style.display = 'none';
            }
        }
    } else {
        console.error('all-reviews-data script element not found.');
        const loadMoreButton = document.getElementById('load-more-button');
        if (loadMoreButton) {
            loadMoreButton.parentElement.style.display = 'none';
        }
    }
    
    // Load more button event listener
    const loadMoreButton = document.getElementById('load-more-button');
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', loadMoreMovies);
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