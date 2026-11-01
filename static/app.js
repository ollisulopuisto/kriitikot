// Kriitikon valinta - Main JavaScript
// =====================================

// Globaalit muuttujat
// ===================
let savedScrollLeft = 0;
let originalTableWidth = 0;
let originalVisibleColumns = 0;
let currentMovieOffset = window.currentMovieOffset || 30; // Aloitetaan 30:stä, koska ensimmäiset 30 on jo ladattu Jinjalla
const movieLimit = 30;
// Fasettien ollessa päällä automaattinen täydennys ja "Lataa lisää" tähtäävät
// tähän määrään aktiivisia fasetteja vastaavia arvosteluja kerrallaan.
const FACET_REVIEW_BATCH = 10;

// Arviomääräliukusäätimen asento -> vähimmäisarviomäärä (myös filters.js käyttää)
const REVIEW_VALUE_MAPPING = { 1: 1, 2: 2, 3: 4, 4: 6, 5: 8 };

// Julkaisujen kokonimet -> suodatin nappien lyhenteet. reviews.jsonin
// source_publication on koko nimi ("Helsingin Sanomat"), kun taas nappien
// data-publication on lyhenne ("HS"). Uudet versiot reviews.jsonista
// sisältävät publication_short-kentän, jolloin kartoitusta ei tarvita.
const PUB_FULL_NAME_TO_SHORT = {
    'HELSINGIN SANOMAT': 'HS',
    'KESKISUOMALAINEN': 'KSML',
    'ILTALEHTI': 'IL',
    'TURUN SANOMAT': 'TS',
    'SUOMEN KUVALEHTI': 'SK',
    'ILTA-SANOMAT': 'IS',
    'FILM-O-HOLIC': 'FILMOHOLIC'
};

// Palauta julkaisun lyhenne (isot kirjaimet) koko nimestä tai lyhenteestä.
function pubShortOf(value) {
    const v = String(value || '').trim().toUpperCase();
    return PUB_FULL_NAME_TO_SHORT[v] || v;
}
let allGroupedReviews = window.allGroupedReviews || {}; // Tähän ladataan kaikki arvostelut JSONista
let movieTitles = Object.keys(allGroupedReviews);
let allCritics = []; // Kaikki kriitikot, tarvitaan renderöintiin (id ja name)
let allCriticsMap = {}; // Map kriitikoista {id: critic_object}
let allPublicationMap = {}; // Map julkaisuista {short_name: publication_object}
window.nytleffaan_urls = window.nytleffaan_urls || {};
window.poster_urls = window.poster_urls || {};
window.letterboxd_urls = window.letterboxd_urls || {};
window.movie_review_counts = window.movie_review_counts || {};
window.movie_rating_distributions = window.movie_rating_distributions || {};



// HTML-suojaus skreipatulle datalle
// =================================
// Arvosteludata (otsikot, tekstit, URL:t) tulee ulkoisilta sivuilta ja
// interpoloidaan HTML-merkkijonoihin. Pako estää tallennetun XSS:n.
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}
// Vain http(s)-URL:t sallitaan href/src-attribuutteihin (estää javascript:-URL:t)
function safeHttpUrl(url) {
    const u = String(url ?? '').trim();
    return /^https?:\/\//i.test(u) ? escapeHtml(u) : '';
}

// Desktop-taulukon laiska rakentaminen
// ====================================
// Taulukko on piilotettu alle 769px leveydellä, joten sen ~2500 solua
// rakennetaan DOMiin vasta kun niitä oikeasti näytetään. Mobiilissa tämä
// säästää DOM-solmujen luonnin ja tyylilaskennan, ja tekee suodattimien
// solukohtaisista silmukoista tyhjiä.

const DESKTOP_MEDIA_QUERY = '(min-width: 769px)';
let desktopTableReady = false;

function isDesktopWidth() {
    if (typeof window.matchMedia === 'function') {
        return window.matchMedia(DESKTOP_MEDIA_QUERY).matches;
    }
    return window.innerWidth >= 769;  // fallback esim. testiympäristöön
}

/**
 * Rakenna desktop-taulukon rivit jos ollaan työpöytäleveydellä.
 * Turvallinen kutsua monta kertaa.
 */
function ensureDesktopTable() {
    if (desktopTableReady || !isDesktopWidth()) return false;

    const tbody = document.querySelector('#review-container-desktop tbody');
    if (!tbody) return false;

    const template = document.getElementById('desktop-rows');
    if (template) {
        tbody.appendChild(template.content.cloneNode(true));
    }
    desktopTableReady = true;

    // Täydennä rivit elokuville jotka on jo ladattu mobiilikortteihin
    const serverRendered = template ? tbody.rows.length : 0;
    if (currentMovieOffset > serverRendered) {
        const pending = movieTitles.slice(serverRendered, currentMovieOffset);
        let html = '';
        pending.forEach(title => {
            if (allGroupedReviews[title]) {
                html += renderMovie(title, allGroupedReviews[title]).desktop;
            }
        });
        if (html) tbody.insertAdjacentHTML('beforeend', html);
    }

    return true;
}

/**
 * Järjestä sarakkeet niin että ylimpien elokuvien arvostelijat tulevat vasemmalle.
 *
 * Tämä on ajettava VASTA kun rivit ovat DOMissa. interactions.js:n initSorting
 * yrittää samaa, mutta se ajetaan defer-skriptinä jolloin document.readyState on
 * jo "interactive" — eli ennen DOMContentLoadedia ja siten ennen kuin rivit on
 * kloonattu templatesta. Silloin se järjestää tyhjän taulukon eikä tee mitään.
 */
function sortColumnsOnceRowsExist() {
    const tbody = document.querySelector('#review-container-desktop tbody');
    if (!tbody || !tbody.rows.length) return;

    if (typeof sortCriticColumnsByReviews === 'function') sortCriticColumnsByReviews();
    if (typeof updateCriticColumnVisibility === 'function') updateCriticColumnVisibility();
}

/**
 * Alusta taulukkoon sidotut toiminnot rivien rakentamisen jälkeen.
 */
function activateDesktopTable() {
    if (!ensureDesktopTable()) return;

    if (typeof initMovieClickHandlers === 'function') initMovieClickHandlers();
    if (typeof initRatingFilterClickHandlers === 'function') initRatingFilterClickHandlers();
    sortColumnsOnceRowsExist();

    document.dispatchEvent(new CustomEvent('table-sorted'));
    window.dispatchEvent(new Event('resize'));
}

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
        nytleffaanLink.rel = 'noopener noreferrer';
        nytleffaanLink.textContent = 'Osta liput';
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
        letterboxdLink.rel = 'noopener noreferrer';
        letterboxdLink.textContent = 'Letterboxd';
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
    
    // Tarkista onko jokin elokuva valittu (klikattu nimeä)
    const selectedMovieRow = tbody.querySelector('tr[data-filtered="true"]');
    
    const visibleRows = Array.from(tbody.querySelectorAll('tr:not(.poster-row)')).filter(row => {
        // Jos jokin elokuva on valittu, huomioidaan vain se sarakenäkyvyydessä
        if (selectedMovieRow) {
            return row === selectedMovieRow;
        }
        return row.style.display !== 'none';
    });

    const starSlider = document.getElementById('star-filter-slider');
    const activeStarFilter = starSlider ? parseInt(starSlider.value) : 1;
    const hasActiveStarFilter = activeStarFilter > 1;

    // Tarkista onko julkaisufiltteri aktiivinen
    const activePubButtons = document.querySelectorAll('.filter-publication.active, .media-filter-btn.active');
    const activePubs = Array.from(new Set(Array.from(activePubButtons).map(btn => btn.dataset.publication)));
    const hasActivePubFilter = activePubs.length > 0;

    // Tarkista onko jokin kriitikko valittu (manuaalinen suodatus)
    const selectedCriticHeader = criticHeaders.find(h => h.dataset.filtered === 'true');
    
    // Käy läpi jokainen kriitikko (sarake)
    criticHeaders.forEach((header) => {
        const criticId = header.dataset.criticId;
        const cellIndex = header.cellIndex;
        if (cellIndex === -1) return;
        
        // JOS jokin kriitikko on valittu, näytetään vain se (ja piilotetaan muut)
        if (selectedCriticHeader) {
            const isSelected = (header === selectedCriticHeader);
            
            header.classList.toggle('filter-hidden', !isSelected);
            header.style.display = isSelected ? '' : 'none';

            Array.from(tbody.rows).forEach(row => {
                const cell = row.cells[cellIndex];
                if (cell) {
                    cell.classList.toggle('filter-hidden', !isSelected);
                    cell.style.display = isSelected ? '' : 'none';
                }
            });
            return; // Siirry seuraavaan headeriin
        }

        const criticName = header.querySelector('.critic-name') ? header.querySelector('.critic-name').textContent.trim() : criticId;
        
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
                const criticPubs = mediaSpan ? mediaSpan.textContent.trim().toUpperCase().split(', ') : [];
                
                // Matches if any of the active filters matches one of critic's pubs
                const matchesPub = activePubs.some(pub => criticPubs.includes(pub.toUpperCase()));
                
                if (!matchesPub) {
                    hasVisibleReview = false;
                } else {
                    hasVisibleReview = checkRowsForReview(visibleRows, cellIndex, hasActiveStarFilter, activeStarFilter, criticName, activePubs);
                }
            } else {
                hasVisibleReview = checkRowsForReview(visibleRows, cellIndex, hasActiveStarFilter, activeStarFilter, criticName, []);
            }
        }

        // Piilota tai näytä sarake
        const tbodyRows = Array.from(tbody.rows);
        if (hasVisibleReview) {
            header.classList.remove('filter-hidden');
            header.style.display = ''; 
            tbodyRows.forEach(row => {
                const cell = row.cells[cellIndex];
                if (cell) {
                    cell.classList.remove('filter-hidden');
                    cell.style.display = ''; 
                }
            });
        } else {
            header.classList.add('filter-hidden');
            tbodyRows.forEach(row => {
                const cell = row.cells[cellIndex];
                if (cell) {
                    cell.classList.add('filter-hidden');
                    // Tärkeää: lisätään myös inline style koska joissain tapauksissa se ohittaa luokan
                    cell.style.display = 'none';
                }
            });
            header.style.display = 'none';
        }
    });

    /**
     * Apufunktio: Tarkista löytyykö sarakkeesta näkyviä arvioita
     */
    function checkRowsForReview(rows, cellIndex, hasStarFilter, starLimit, criticName, activePubs) {
        const hasActivePubFilter = activePubs && activePubs.length > 0;
        
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            
            // VARMISTUS: Älä tarkista piilotettuja rivejä
            if (row.style.display === 'none') continue;
            
            const cell = row.cells[cellIndex];
            if (!cell) continue;

            // Arvostelut tässä solussa (sekä tähdet että tekstiarviot)
            const allReviews = cell.querySelectorAll('.rating-pill, .no-rating');
            
            if (allReviews.length === 0) {
                // Erityistapaus: jos solussa on pelkkää tekstiä ilman luokkaa tai se on viiva
                const text = cell.textContent.trim();
                const isEmpty = text === '–' || text === '';
                if (isEmpty) continue;
                
                // Jos ei ole tähtiä (pelkkää tekstiä), se matchaa vain jos tähti-raja on 1
                if (hasStarFilter && starLimit > 1) continue;
                
                // Jos ei ole luokkaa, ei ole julkaisutietoakaan saatavilla tässä
                if (hasActivePubFilter) continue;
                
                return true;
            }

            // Jos julkaisufiltteri tai tähtifiltteri on päällä, tarkista onko tässä solussa sellaista arviota
            let hasMatchingReviewInCell = false;
            
            allReviews.forEach(el => {
                const isNoRating = el.classList.contains('no-rating');
                
                // Tarkista tähti-match
                if (hasStarFilter) {
                    if (isNoRating) {
                        // Tekstiarvio matchaa vain jos tähti-raja on 1
                        if (starLimit > 1) return;
                    } else {
                        const starText = el.querySelector('.rating-stars')?.textContent || el.textContent;
                        const starCount = (starText.match(/★/g) || []).length;
                        if (starCount < starLimit) return; // Jatka seuraavaan
                    }
                }
                
                // Tarkista julkaisu-match
                if (hasActivePubFilter) {
                    const revPub = pubShortOf(el.dataset.publication);
                    if (!activePubs.some(pub => revPub === pub.toUpperCase())) return;
                }
                
                hasMatchingReviewInCell = true;
            });
            
            if (hasMatchingReviewInCell) return true;
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

    // Tarkista onko jokin elokuva valittu (klikattu nimeä)
    const selectedMovieRow = tbody.querySelector('tr[data-filtered="true"]');

    allRows.forEach(row => {
        // Jos jokin elokuva on valittu, näytetään VAIN se ja piilotetaan kaikki muut
        if (selectedMovieRow) {
            if (row === selectedMovieRow) {
                row.style.display = '';
                row.classList.remove('dimmed');
            } else {
                row.style.display = 'none';
                row.classList.add('dimmed');
            }
            return;
        }

        // Jos rivi on jo piilotettu muista syistä (esim. tekstihaku, tähdet), älä koske
        // Mutta meidän pitää erottaa "ei arvosteluja" -piilotus "filtteri"-piilotuksesta logic chainissa.
        // Tässä oletamme, että tämä ajetaan viimeisenä.

        // Emme koske riveihin, jotka on piilotettu review-count, star tai publication filtterillä
        if (row.dataset.reviewCountFiltered === 'true' || row.dataset.starFiltered === 'true' || row.dataset.publicationFiltered === 'true') {
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

    // Päivitä "Lataa lisää" -napin näkyvyys
    const loadMoreButton = document.getElementById('load-more-button');
    if (loadMoreButton) {
        if (selectedMovieRow) {
            // Piilota nappi jos olemme yksittäisen elokuvan näkymässä (desktop)
            loadMoreButton.parentElement.style.display = 'none';
        } else {
            updateLoadMoreVisibility();
        }
    }
}

// Lazy Loading
// ============

function createReviewPill(review) {
    const tooltipText = escapeHtml(review.review_text ? review.review_text.substring(0, 200) : 'Lue arvostelu');
    let starsHtml = '★'.repeat(review.rating_stars);
    const publicationName = escapeHtml(allPublicationMap[review.source_publication]?.name || review.source_publication); // Get full name
    const pubId = review.publication_short || review.source_publication;
    const pubAttr = pubId ? `data-publication="${escapeHtml(pubId)}"` : '';
    
    const safeReviewUrl = safeHttpUrl(review.source_url);
    if (safeReviewUrl) {
        return `
            <a href="${safeReviewUrl}"
                class="rating-link rating-pill stars-${escapeHtml(review.rating_stars)}" ${pubAttr} target="_blank"
                title="${publicationName}: ${tooltipText}...">
                <span class="rating-stars">${starsHtml}</span>
            </a>
        `;
    } else {
        return `
            <span class="rating-pill stars-${escapeHtml(review.rating_stars)}" ${pubAttr}>
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
    const posterUrl = safeHttpUrl(window.poster_urls[movieTitle]);
    const letterboxdUrl = safeHttpUrl(window.letterboxd_urls[movieTitle]);
    const nytleffaanUrl = safeHttpUrl(window.nytleffaan_urls[movieTitle]);
    const safeMovieTitle = escapeHtml(movieTitle);
    const movieReviewCount = window.movie_review_counts[movieTitle];

    let calculatedReviewCount = 0;
    if (criticsReviewsDict) {
        Object.values(criticsReviewsDict).forEach(reviews => {
            if (reviews && reviews.length > 0) {
                calculatedReviewCount += reviews.length;
            }
        });
    }

    const dist = window.movie_rating_distributions[movieTitle] || [];
    const buildSparklineHtml = (distribution, extraClasses = '') => {
        const hasDistribution = distribution.length === 5 && distribution.some(count => count > 0);
        if (!hasDistribution) {
            return '';
        }
        const maxDist = Math.max(...distribution);
        const classes = ['movie-sparkline', extraClasses].filter(Boolean).join(' ');
        const label = 'Arvosanojen jakauma: ' +
            distribution.map((count, i) => `${i + 1}★ ${count}`).join(', ');
        return `
            <div class="${classes}" role="img" aria-label="${label}" title="${label}">
                ${distribution.map((count, i) => `
                    <div class="spark-bar-container">
                        <div class="spark-bar spark-bar-${i + 1}${count === 0 ? ' spark-bar--empty' : ''}" style="height: ${maxDist > 0 ? (count / maxDist * 100) : 0}%"></div>
                    </div>
                `).join('')}
            </div>
        `;
    };
    const sparklineHtml = buildSparklineHtml(dist);
    const mobileSparklineHtml = buildSparklineHtml(dist, 'movie-card-sparkline');

    // Desktop row
    let desktopHtml = `
        <tr data-review-count="${calculatedReviewCount}">
            <td class="movie-col" data-poster="${posterUrl}"
                data-letterboxd="${letterboxdUrl}"
                data-nytleffaan="${nytleffaanUrl}">
                <div class="movie-content-wrapper">
                    ${posterUrl ? `
                    <div class="movie-poster-container">
                        <img src="${posterUrl}" alt="${safeMovieTitle} juliste" class="movie-poster-thumb" loading="lazy" decoding="async" width="48" height="72">
                        <img data-src="${posterUrl}" alt="${safeMovieTitle} juliste" class="movie-poster-full" loading="lazy" decoding="async">
                    </div>
                    ` : ''}
                    <div class="movie-info">
                        <div class="movie-title-main">${safeMovieTitle}</div>
                        <div class="movie-meta-row">
                            ${movieReviewCount ? `<div class="movie-review-count">🎬 ${movieReviewCount}</div>` : ''}
                            ${sparklineHtml}
                            ${nytleffaanUrl ? `<a href="${nytleffaanUrl}" target="_blank" rel="noopener noreferrer" class="movie-link nytleffaan-link" title="Osta liput: nytleffaan.fi">Osta liput</a>` : ''}
                            ${letterboxdUrl ? `<a href="${letterboxdUrl}" target="_blank" rel="noopener noreferrer" class="movie-link letterboxd-link" title="Katso Letterboxd:ssä">Letterboxd</a>` : ''}
                        </div>
                    </div>
                </div>
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
        <div class="movie-card" data-movie="${safeMovieTitle}" data-poster="${posterUrl}" data-review-count="${calculatedReviewCount}">
            <div class="movie-card-header">
                    <div class="movie-card-title-row">
                        <div class="movie-card-title">${safeMovieTitle}</div>
                        <div class="movie-card-summary">
                        ${movieReviewCount ? `<div class="movie-card-review-count">🎬 ${movieReviewCount}</div>` : ''}
                        ${mobileSparklineHtml}
                        </div>
                        ${posterUrl ? `
                            <div class="movie-card-poster-container">
                                <img class="movie-card-poster-thumb" src="${posterUrl}" alt="${safeMovieTitle} poster" loading="lazy" decoding="async" width="100" height="150" />
                            </div>
                        ` : ''}
                    </div>
            </div>
            <div class="movie-card-body">
    `;
    // Populate with critics from allCritics (global, ordered list)
    allCritics.forEach(critic => {
        if (criticsReviewsDict[critic.name]) {
            criticsReviewsDict[critic.name].forEach(review => {
                mobileHtml += `
                    <div class="review-item" data-critic="${escapeHtml(critic.id)}"
                        data-publication="${escapeHtml(review.publication_short || review.source_publication)}">
                        <div class="review-critic">
                            <div class="review-critic-top">
                                <span class="review-critic-name">${escapeHtml(critic.name)}</span>
                            </div>
                            <div class="review-media">${escapeHtml(review.source_publication.toUpperCase())}</div>
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
            mobileHtml += `<a href="${nytleffaanUrl}" target="_blank" rel="noopener noreferrer" class="movie-link nytleffaan-link">Osta liput</a>`;
        }
        if (letterboxdUrl) {
            mobileHtml += `<a href="${letterboxdUrl}" target="_blank" rel="noopener noreferrer" class="movie-link letterboxd-link">Letterboxd</a>`;
        }
        mobileHtml += `</div>`;
    }
    mobileHtml += `</div></div>`;

    return { desktop: desktopHtml, mobile: mobileHtml };
}


/**
 * Lue kriitikkojen järjestys taulukon otsikoista.
 *
 * Sarakkeet järjestetään uudelleen sivun latauksessa (sortCriticColumnsByReviews)
 * niin että ylimpien elokuvien arvostelijat tulevat vasemmalle. Se tapahtuu vasta
 * app.js:n DOMContentLoaded-käsittelijän JÄLKEEN, joten tähän talletettu järjestys
 * vanhentuu. Jos uudet rivit renderöidään vanhentuneessa järjestyksessä, solut
 * osuvat väärien otsikoiden alle ja sarakkeiden näkyvyyslogiikka menee sekaisin.
 */
function syncCriticOrderFromDom() {
    const headers = document.querySelectorAll('thead th.rating-cell');
    if (!headers.length) return;

    allCritics = Array.from(headers).map(th => ({
        id: th.dataset.criticId,
        name: th.querySelector('.critic-name') ? th.querySelector('.critic-name').textContent : ''
    }));
    allCriticsMap = {};
    allCritics.forEach(c => { allCriticsMap[c.id] = c; });
}

function loadMoreMovies(batchSize = movieLimit) {
    if (typeof batchSize !== 'number') batchSize = movieLimit;
    const loadMoreButton = document.getElementById('load-more-button');
    if (!loadMoreButton) return;

    if (typeof window.currentMovieOffset === 'number') {
        currentMovieOffset = window.currentMovieOffset;
    }

    // Varmista että solut renderöidään otsikoiden nykyisessä järjestyksessä
    syncCriticOrderFromDom();

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

    const moviesToRender = movieTitles.slice(currentMovieOffset, currentMovieOffset + batchSize);

    if (moviesToRender.length === 0) {
        loadMoreButton.parentElement.style.display = 'none';
        loadMoreButton.disabled = false;
        loadMoreButton.textContent = originalText;
        return;
    }

    // Desktop-rivit rakennetaan vain jos taulukko on käytössä; mobiilissa
    // ne odottavat kunnes ikkuna levenee (ensureDesktopTable täydentää ne)
    let desktopHtml = '';
    let mobileHtml = '';
    moviesToRender.forEach(movieTitle => {
        const criticsReviewsDict = allGroupedReviews[movieTitle];
        const { desktop, mobile } = renderMovie(movieTitle, criticsReviewsDict);

        if (desktopTableReady) desktopHtml += desktop;
        mobileHtml += mobile;
    });

    if (desktopHtml) desktopTbody.insertAdjacentHTML('beforeend', desktopHtml);
    mobileCardsContainer.insertAdjacentHTML('beforeend', mobileHtml);

    currentMovieOffset += moviesToRender.length;
    window.currentMovieOffset = currentMovieOffset;

    updateLoadMoreVisibility();

    // Re-initialize event handlers for newly added elements
    if (typeof initMovieClickHandlers === 'function') initMovieClickHandlers();
    if (typeof initMobileCriticClickHandlers === 'function') initMobileCriticClickHandlers();
    if (typeof initRatingFilterClickHandlers === 'function') initRatingFilterClickHandlers();
    if (typeof initReviewCountFilter === 'function') initReviewCountFilter();
    if (typeof initStarFilter === 'function') initStarFilter();
    if (typeof initResetButton === 'function') initResetButton();
    if (typeof initFavoriteFilter === 'function') initFavoriteFilter();
    
    if (typeof window.reapplyAllFacets === 'function') window.reapplyAllFacets();
    if (typeof updateCriticColumnVisibility === 'function') updateCriticColumnVisibility();
    if (window.reconcileFacetVisibility) window.reconcileFacetVisibility();
    
    loadMoreButton.disabled = false;
    loadMoreButton.textContent = originalText;
}


// Aktiivisten fasettien tila, luettuna DOM:sta samoin perustein kuin
// filters.js:n reconcileFacetVisibility ne tulkitsee.
function currentFacetState() {
    const selectedHeader = document.querySelector('thead th.rating-cell[data-filtered="true"]');
    const pubs = [...new Set([...document.querySelectorAll('.filter-publication.active, .media-filter-btn.active')]
        .map(b => (b.dataset.publication || '').toUpperCase()))];
    const minStars = Number(document.getElementById('star-filter-slider')?.value || 1);
    const rcPos = Number(document.getElementById('min-reviews-slider')?.value || 1);
    const minReviews = REVIEW_VALUE_MAPPING[rcPos] || rcPos;
    const favoritesOn = !!window.isFavoritesFilterActive?.();
    const chosenCard = document.querySelector('.movie-card[data-filtered="true"]');
    const chosenRow = document.querySelector('tbody tr[data-filtered="true"]');
    const chosenMovie = chosenCard?.dataset.movie
        || chosenRow?.querySelector('.movie-title-main')?.textContent.trim()
        || null;
    return { criticId: selectedHeader?.dataset.criticId || null, pubs, minStars, minReviews, favoritesOn, chosenMovie };
}

// Onko jokin hakufasetti päällä? (Yksittäisen elokuvan valinta ei ole fasetti.)
function facetFiltersActive() {
    const st = currentFacetState();
    return !!(st.criticId || st.pubs.length || st.minStars > 1 || st.minReviews > 1 || st.favoritesOn);
}

// Täsmääkö yksittäinen arvostelu aktiivisiin fasetteihin? Peilaa
// reconcileFacetVisibilityn matches()-logiikkaa puhtaaseen dataan,
// jotta lataamattomien elokuvien osumat voidaan laskea renderöimättä.
function reviewMatchesFacetState(review, criticName, st) {
    const critic = allCritics.find(c => c.name === criticName);
    const criticId = critic ? critic.id : null;
    if (st.criticId && criticId !== st.criticId) return false;
    if (st.favoritesOn && !(criticId && window.isFavoriteCritic?.(criticId))) return false;
    if (st.pubs.length && !st.pubs.includes(pubShortOf(review.publication_short || review.source_publication))) return false;
    if (st.minStars > 1 && !(Number(review.rating_stars) >= st.minStars)) return false;
    return true;
}

function movieHasFacetMatch(movieTitle, st) {
    if (st.chosenMovie && movieTitle !== st.chosenMovie) return false;
    const dict = allGroupedReviews[movieTitle];
    if (!dict) return false;
    if (st.minReviews > 1) {
        let total = 0;
        Object.values(dict).forEach(rs => { total += rs ? rs.length : 0; });
        if (total < st.minReviews) return false;
    }
    return Object.entries(dict).some(([criticName, rs]) =>
        (rs || []).some(r => reviewMatchesFacetState(r, criticName, st)));
}

// Onko lataamattomassa datassa vielä fasetteja vastaavia arvosteluja?
function tailHasFacetMatches() {
    const st = currentFacetState();
    return movieTitles.slice(currentMovieOffset).some(t => movieHasFacetMatch(t, st));
}

// Ladattujen elokuvien fasetteja vastaavien arvostelujen määrä (puhdas
// datalaskenta, riippumaton siitä mikä on parhaillaan näkyvissä).
function loadedMatchingReviewCount() {
    const st = currentFacetState();
    let n = 0;
    movieTitles.slice(0, currentMovieOffset).forEach(title => {
        const dict = allGroupedReviews[title];
        if (!dict || !movieHasFacetMatch(title, st)) return;
        Object.entries(dict).forEach(([criticName, rs]) => {
            (rs || []).forEach(r => { if (reviewMatchesFacetState(r, criticName, st)) n++; });
        });
    });
    return n;
}

// Näkyvissä olevien fasetteja vastaavien arvostelujen määrä. Mobiilikortit
// renderöidään aina (myös desktopilla), joten ne ovat luotettava lähde.
function matchingVisibleReviewCount() {
    let n = 0;
    document.querySelectorAll('.movie-card').forEach(card => {
        if (card.style.display === 'none') return;
        card.querySelectorAll('.review-item').forEach(item => {
            if (item.style.display !== 'none') n++;
        });
    });
    return n;
}

// "Lataa lisää" -napin näkyvyys: ilman fasetteja näytetään kun dataa on
// lataamatta; fasettien kanssa kun paljastamattomia osumia on vielä jäljellä
// (joko ladattujen joukossa eräpiilotettuna tai lataamattomassa datassa).
function updateLoadMoreVisibility() {
    const btn = document.getElementById('load-more-button');
    if (!btn) return;
    let show;
    if (facetFiltersActive()) {
        show = document.querySelector('.movie-card[data-batch-filtered="true"]') !== null
            || (currentMovieOffset < movieTitles.length && tailHasFacetMatches());
    } else {
        show = currentMovieOffset < movieTitles.length;
    }
    btn.parentElement.style.display = show ? 'block' : 'none';
}

// Kuinka monta fasetteja vastaavaa arvostelua on tällä hetkellä paljastettu.
// Kasvaa FACET_REVIEW_BATCH-erissä käyttäjän painellessa "Lataa lisää".
let facetRevealCount = FACET_REVIEW_BATCH;

// Rajaa näkyvissä olevat osumat facetRevealCountiin. Elokuvarajat säilyvät
// ehjinä: elokuva, jossa eräraja ylittyy, näytetään kokonaan (erä voi siksi
// ylittää tavoitteen viimeisen elokuvan ylimääräisillä osumilla). Ajetaan
// aina reconcileFacetVisibilityn jälkeen, joka on näkyvyyden lopullinen lähde.
function applyFacetBatchVisibility() {
    const cards = [...document.querySelectorAll('.movie-card')];
    if (facetFiltersActive()) {
        let acc = 0;
        cards.forEach(card => {
            delete card.dataset.batchFiltered;
            if (card.style.display === 'none') return;
            const items = [...card.querySelectorAll('.review-item')].filter(i => i.style.display !== 'none');
            if (!items.length) return;
            if (acc >= facetRevealCount) {
                card.dataset.batchFiltered = 'true';
                card.style.display = 'none';
            } else {
                acc += items.length;
            }
        });
    } else {
        cards.forEach(card => { delete card.dataset.batchFiltered; });
    }
    // Peilaa eräpiilotus desktop-riveihin korttien mukaisesti
    const cardByTitle = new Map(cards.map(c => [c.dataset.movie, c]));
    document.querySelectorAll('#review-container-desktop tbody tr:not(.poster-row)').forEach(row => {
        const title = row.querySelector('.movie-title-main')?.textContent.trim();
        const card = title ? cardByTitle.get(title) : null;
        if (!card) return;
        if (card.dataset.batchFiltered === 'true') {
            row.dataset.batchFiltered = 'true';
            row.style.display = 'none';
        } else if (row.dataset.batchFiltered === 'true') {
            delete row.dataset.batchFiltered;
            row.style.display = card.style.display === 'none' ? 'none' : '';
        }
    });
    updateLoadMoreVisibility();
}

// Fasettien ollessa päällä "Lataa lisää" paljastaa seuraavan FACET_REVIEW_BATCH
// osuvan arvostelun erän, lataen tarvittaessa lisää elokuvia taustalla.
function loadMoreFacetAware() {
    facetRevealCount += FACET_REVIEW_BATCH;
    while (loadedMatchingReviewCount() < facetRevealCount && currentMovieOffset < movieTitles.length) {
        const prev = currentMovieOffset;
        loadMoreMovies(movieLimit);
        if (currentMovieOffset <= prev) break;
    }
    window.reapplyAllFacets?.();
    if (sliderWindows && sliderWindowKey) {
        sliderWindows.set(sliderWindowKey, { offset: window.currentMovieOffset ?? currentMovieOffset, reveal: facetRevealCount });
    }
    updateLoadMoreVisibility();
}

// Facet top-ups are temporary pagination windows, remembered per facet state.
let sliderWindows = null;
let sliderWindowKey = null;
let sliderBaseOffset = null;
let sliderBaseKey = null;
function sliderResultsKey() {
    return JSON.stringify([
        document.getElementById('min-reviews-slider')?.value,
        document.getElementById('star-filter-slider')?.value,
        [...document.querySelectorAll('.media-filter-btn.active, .filter-publication.active')].map(e => e.dataset.publication).sort(),
        document.querySelector('thead th[data-filtered="true"]')?.dataset.criticId,
        !!window.isFavoritesFilterActive?.(),
        [...document.querySelectorAll('thead th.rating-cell')].filter(h => window.isFavoriteCritic?.(h.dataset.criticId)).map(h => h.dataset.criticId).sort(),
        document.querySelector('.movie-card[data-filtered="true"]')?.dataset.movie
    ]);
}
function rememberSliderWindow() {
    if (sliderWindows) return;
    sliderWindows = new Map();
    sliderBaseOffset = window.currentMovieOffset ?? currentMovieOffset;
    sliderWindowKey = sliderResultsKey();
    sliderBaseKey = sliderWindowKey;
    sliderWindows.set(sliderWindowKey, { offset: sliderBaseOffset, reveal: FACET_REVIEW_BATCH });
}
function topUpSliderResults() {
    // Initialization and pagination reapplication never enter this function.
    if (!sliderWindows) return;
    sliderWindows.set(sliderWindowKey, { offset: window.currentMovieOffset ?? currentMovieOffset, reveal: facetRevealCount });
    const key = sliderResultsKey();
    const restoring = sliderWindows.has(key);
    const saved = sliderWindows.get(key) || { offset: sliderBaseOffset, reveal: FACET_REVIEW_BATCH };
    const offset = saved.offset;
    const keep = new Set(movieTitles.slice(0, offset));
    document.querySelectorAll('.movie-card').forEach(card => {
        if (!keep.has(card.dataset.movie)) card.remove();
    });
    document.querySelectorAll('#review-container-desktop tbody tr').forEach(row => {
        const title = row.querySelector('.movie-title-main')?.textContent.trim();
        if (title && !keep.has(title)) row.remove();
    });
    const rendered = document.querySelectorAll('.movie-card').length;
    currentMovieOffset = Math.min(rendered, offset);
    window.currentMovieOffset = currentMovieOffset;
    if (currentMovieOffset < offset) loadMoreMovies(offset - currentMovieOffset);
    sliderWindowKey = key;
    facetRevealCount = saved.reveal;
    window.reapplyAllFacets?.();
    const facetsActive = facetFiltersActive();
    if (!restoring && facetsActive) {
        // Varmista että ladattujen joukossa riittää osumia erätavoitteeseen
        while (loadedMatchingReviewCount() < facetRevealCount && currentMovieOffset < movieTitles.length) {
            const before = currentMovieOffset;
            loadMoreMovies(movieLimit);
            if (currentMovieOffset <= before) break;
        }
    } else if (!restoring && !facetsActive) {
        const visibleCount = () => [...document.querySelectorAll('.movie-card')].filter(card => card.style.display !== 'none').length;
        while (visibleCount() < movieLimit && currentMovieOffset < movieTitles.length) {
            const before = currentMovieOffset;
            loadMoreMovies(movieLimit - visibleCount());
            if (currentMovieOffset <= before) break;
        }
    }
    // reapplyAllFacets ajaa reconcileFacetVisibilityn, joka soveltaa
    // eränäkyvyyden (applyFacetBatchVisibility) lopuksi
    window.reapplyAllFacets?.();
    sliderWindows.set(key, { offset: currentMovieOffset, reveal: facetRevealCount });
    updateLoadMoreVisibility();
}
window.rememberSliderWindow = rememberSliderWindow;
window.topUpSliderResults = topUpSliderResults;


document.addEventListener('DOMContentLoaded', () => {
    // Versio-logi
    const versionMeta = document.querySelector('meta[name="version"]');
    if (versionMeta) {
        console.log(`🎬 Kriitikon valinta v${versionMeta.content} käynnistyy...`);
    }

    // Rakenna desktop-taulukko ja järjestä sarakkeet vasta nyt: rivit tulevat
    // templatesta, joten ne eivät ole olemassa kun defer-skriptit ajetaan
    ensureDesktopTable();
    sortColumnsOnceRowsExist();

    // Haetaan kriitikkojen tiedot taulukon headerista
    const criticHeaders = document.querySelectorAll('thead th.rating-cell');
    allCritics = Array.from(criticHeaders).map(th => ({
        id: th.dataset.criticId,
        name: th.querySelector('.critic-name').textContent
    }));
    allCritics.forEach(c => allCriticsMap[c.id] = c);

    // Julkaisujen nimet suodatinnapeista (short_name -> koko nimi)
    document.querySelectorAll('.media-filter-btn').forEach(btn => {
        const short_name = btn.dataset.publication.toLowerCase();
        const name = btn.textContent.trim();
        allPublicationMap[short_name] = { short_name: short_name, name: name };
    });

    // Movie meta info (poster, letterboxd, nytleffaan, review counts, sparklines)
    const movieMetaElement = document.getElementById('movie-meta-data');
    if (movieMetaElement) {
        try {
            const movieMetaData = JSON.parse(movieMetaElement.textContent);
            window.nytleffaan_urls = movieMetaData.nytleffaan_urls || {};
            window.poster_urls = movieMetaData.poster_urls || {};
            window.letterboxd_urls = movieMetaData.letterboxd_urls || {};
            window.movie_review_counts = movieMetaData.movie_review_counts || {};
            window.movie_rating_distributions = movieMetaData.movie_rating_distributions || {};
        } catch (e) {
            console.error('Error parsing movie-meta-data:', e);
        }
    }

    // Extract from initial Jinja-rendered movie cells
    document.querySelectorAll('#review-container-desktop tbody tr .movie-col').forEach(movieCol => {
        const titleEl = movieCol.querySelector('.movie-title-main');
        if (!titleEl) return;
        const movieTitle = titleEl.textContent;
        if (!window.nytleffaan_urls[movieTitle]) {
            window.nytleffaan_urls[movieTitle] = movieCol.dataset.nytleffaan;
        }
        if (!window.poster_urls[movieTitle]) {
            window.poster_urls[movieTitle] = movieCol.dataset.poster;
        }
        if (!window.letterboxd_urls[movieTitle]) {
            window.letterboxd_urls[movieTitle] = movieCol.dataset.letterboxd;
        }
        const countElem = movieCol.querySelector('.movie-review-count');
        if (countElem && !window.movie_review_counts[movieTitle]) {
            window.movie_review_counts[movieTitle] = parseInt(countElem.textContent.replace('🎬 ', ''));
        }
    });

    // Lataa loput arvostelut: inline-data jos sivulla on sellainen (testit,
    // vanha sivupohja), muuten erillinen JSON-tiedosto joka ei blokkaa ensirenderöintiä
    const hideLoadMore = () => {
        const btn = document.getElementById('load-more-button');
        if (btn) btn.parentElement.style.display = 'none';
    };
    const applyReviewsData = (data) => {
        allGroupedReviews = data;
        movieTitles = Object.keys(allGroupedReviews);
        loadMoreMovies();
    };

    const inlineData = document.getElementById('all-reviews-data');
    if (inlineData) {
        try {
            applyReviewsData(JSON.parse(inlineData.textContent));
        } catch (e) {
            console.error('Error parsing all-reviews-data:', e);
            hideLoadMore();
        }
    } else {
        fetch('reviews.json')
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(applyReviewsData)
            .catch(e => {
                console.error('Error loading reviews.json:', e);
                hideLoadMore();
            });
    }

    // Load more button event listener: fasettien kanssa ladataan seuraava
    // erä fasetteja vastaavia arvosteluja, muuten raakaa elokuvaerää.
    const loadMoreButton = document.getElementById('load-more-button');
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', () => {
            if (facetFiltersActive()) {
                loadMoreFacetAware();
            } else {
                loadMoreMovies();
                // Suodattamaton manuaalinen lataus kasvattaa perusikkunaa,
                // jotta fasetin poiston palautus säilyttää käyttäjän lataamat.
                if (sliderWindows && sliderBaseKey === sliderResultsKey()) {
                    sliderBaseOffset = window.currentMovieOffset ?? currentMovieOffset;
                    sliderWindows.set(sliderBaseKey, { offset: sliderBaseOffset, reveal: FACET_REVIEW_BATCH });
                }
            }
        });
    }

    // Mobile poster toggle functionality
    initMobilePosterToggle();

    // Kun ikkuna levenee työpöytäkokoon (esim. tabletin kääntö), rakenna taulukko
    if (typeof window.matchMedia === 'function') {
        const desktopMedia = window.matchMedia(DESKTOP_MEDIA_QUERY);
        const onBreakpointChange = (e) => {
            if (e.matches) activateDesktopTable();
        };
        if (desktopMedia.addEventListener) {
            desktopMedia.addEventListener('change', onBreakpointChange);
        } else if (desktopMedia.addListener) {
            desktopMedia.addListener(onBreakpointChange);  // Safari < 14
        }
    }

    // Desktop: lataa iso hover-juliste vasta kun hiiri osuu julisteeseen
    document.addEventListener('mouseover', (e) => {
        const container = e.target.closest('.movie-poster-container');
        if (!container) return;
        const fullPoster = container.querySelector('.movie-poster-full[data-src]');
        if (fullPoster) {
            fullPoster.src = fullPoster.dataset.src;
            fullPoster.removeAttribute('data-src');
        }
    });
});

/**
 * Initialize mobile poster tap-to-toggle functionality with lightbox
 */
function initMobilePosterToggle() {
    const lightbox = document.getElementById('poster-lightbox');
    const lightboxImg = document.getElementById('poster-lightbox-img');
    const closeBtn = lightbox ? lightbox.querySelector('.poster-lightbox-close') : null;
    const backdrop = lightbox ? lightbox.querySelector('.poster-lightbox-backdrop') : null;

    if (!lightbox || !lightboxImg) return;

    // Open lightbox when clicking poster thumbnail
    document.addEventListener('click', function(e) {
        const posterContainer = e.target.closest('.movie-card-poster-container');
        if (!posterContainer) return;

        e.preventDefault();
        e.stopPropagation();

        // Get poster URL from parent movie card
        const movieCard = posterContainer.closest('.movie-card');
        if (!movieCard) return;

        const posterUrl = movieCard.dataset.poster;
        if (!posterUrl) return;

        // Show lightbox
        lightboxImg.src = posterUrl;
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    });

    // Close lightbox on close button click
    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            closeLightbox();
        });
    }

    // Close lightbox on backdrop click
    if (backdrop) {
        backdrop.addEventListener('click', function(e) {
            e.stopPropagation();
            closeLightbox();
        });
    }

    // Close lightbox on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && lightbox.style.display === 'flex') {
            closeLightbox();
        }
    });

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
        lightboxImg.src = ''; // Clear image to save memory
    }
}


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
window.ensureDesktopTable = ensureDesktopTable;
window.activateDesktopTable = activateDesktopTable;
window.isDesktopWidth = isDesktopWidth;
window.syncCriticOrderFromDom = syncCriticOrderFromDom;
window.loadMoreMovies = loadMoreMovies;
window.loadMoreFacetAware = loadMoreFacetAware;
window.applyFacetBatchVisibility = applyFacetBatchVisibility;
window.loadedMatchingReviewCount = loadedMatchingReviewCount;
window.updateLoadMoreVisibility = updateLoadMoreVisibility;
window.pubShortOf = pubShortOf;
window.facetFiltersActive = facetFiltersActive;
window.matchingVisibleReviewCount = matchingVisibleReviewCount;
window.tailHasFacetMatches = tailHasFacetMatches;
window.REVIEW_VALUE_MAPPING = REVIEW_VALUE_MAPPING;
window.FACET_REVIEW_BATCH = FACET_REVIEW_BATCH;

// Sarakkeiden uudelleenjärjestys mitätöi talletetun kriitikkojärjestyksen
document.addEventListener('table-sorted', syncCriticOrderFromDom);
