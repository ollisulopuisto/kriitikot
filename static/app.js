// Kriitikon valinta - Main JavaScript
// =====================================

// Globaalit muuttujat
// ===================
let savedScrollLeft = 0;
let originalTableWidth = 0;
let originalVisibleColumns = 0;

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
    // Tarkista onko linkkejä
    const linksDiv = movieCell.querySelector('.movie-links');
    if (linksDiv) {
        // Tallenna elokuvan nimi
        const titleDiv = movieCell.querySelector('.movie-title-text');
        const movieTitle = titleDiv ? titleDiv.textContent.trim() : movieCell.textContent.trim();
        
        // Palauta vain elokuvan nimi
        movieCell.innerHTML = '';
        movieCell.textContent = movieTitle;
    }
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
    const allRows = Array.from(tbody.querySelectorAll('tr'));
    
    const starSlider = document.getElementById('star-filter-slider');
    const activeStarFilter = starSlider ? parseInt(starSlider.value) : 1;
    const hasActiveStarFilter = activeStarFilter > 1;
    
    console.log(`🔍 updateCriticColumnVisibility: activeStarFilter=${activeStarFilter}, hasActiveStarFilter=${hasActiveStarFilter}`);
    
    // Käy läpi jokainen kriitikko (sarake)
    criticHeaders.forEach((header, index) => {
        const columnIndex = index + 1;
        const criticName = header.textContent.trim().split('\n')[0];
        let hasQualifyingReview = false;
        let reviewsFound = [];
        
        // Tarkista KAIKKI rivit taulukossa
        allRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const cell = cells[columnIndex];
            
            if (cell) {
                const hasLink = cell.querySelector('a.rating-link');
                const ratingStars = cell.querySelector('.rating-stars');
                const noRating = cell.querySelector('.no-rating');
                const isEmpty = noRating && noRating.textContent.trim() === '–';
                
                // Tarkista onko solussa mitään sisältöä
                const hasContent = (hasLink || ratingStars) || (noRating && !isEmpty);
                
                if (hasContent) {
                    // Jos tähtifiltteri on aktiivinen, vaadi vähintään N tähteä
                    if (hasActiveStarFilter) {
                        if (ratingStars) {
                            const starCount = (ratingStars.textContent.match(/★/g) || []).length;
                            reviewsFound.push(starCount);
                            if (starCount >= activeStarFilter) {
                                hasQualifyingReview = true;
                            }
                        }
                        // Jos ei ole tähtiä mutta on muuta sisältöä, älä laske
                    } else {
                        // Ei tähtifiltteröintiä, näytä kaikki jossa on sisältöä
                        hasQualifyingReview = true;
                    }
                }
            }
        });
        
        if (hasActiveStarFilter) {
            if (!hasQualifyingReview && reviewsFound.length > 0) {
                console.log(`🚫 Piilotetaan ${criticName}: arvostelut ${reviewsFound.join(',')}⭐, ei yhtään ${activeStarFilter}⭐`);
            } else if (hasQualifyingReview) {
                console.log(`✅ Näytetään ${criticName}: löytyi vähintään ${activeStarFilter}⭐ arvostelu`);
            }
        }
        
        // Piilota tai näytä sarake
        if (hasQualifyingReview) {
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
    
    // Synkronoi filter-hidden luokat myös kloonattuun sticky headeriin
    const stickyTheadClone = document.getElementById('sticky-thead-clone');
    if (stickyTheadClone) {
        const clonedCriticRow = stickyTheadClone.querySelector('tr.critic-row');
        if (clonedCriticRow) {
            const clonedHeaders = clonedCriticRow.querySelectorAll('th:not(.movie-col)');
            criticHeaders.forEach((header, index) => {
                if (clonedHeaders[index]) {
                    if (header.classList.contains('filter-hidden')) {
                        clonedHeaders[index].classList.add('filter-hidden');
                    } else {
                        clonedHeaders[index].classList.remove('filter-hidden');
                    }
                    
                    // Synkronoi myös even/odd väritys
                    clonedHeaders[index].classList.remove('even-column', 'odd-column');
                    if (header.classList.contains('even-column')) {
                        clonedHeaders[index].classList.add('even-column');
                    }
                    if (header.classList.contains('odd-column')) {
                        clonedHeaders[index].classList.add('odd-column');
                    }
                }
            });
        }
    }
    
    // Päivitä "joka toinen" -väritys
    const visibleHeaders = Array.from(criticHeaders).filter(header => 
        !header.classList.contains('filter-hidden') && header.style.display !== 'none'
    );
    
    criticHeaders.forEach(header => {
        header.classList.remove('even-column', 'odd-column');
    });
    
    visibleHeaders.forEach((header, visibleIndex) => {
        if (visibleIndex % 2 === 0) {
            header.classList.add('even-column');
        } else {
            header.classList.add('odd-column');
        }
        
        const columnIndex = Array.from(criticHeaders).indexOf(header) + 1;
        tbody.querySelectorAll('tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells[columnIndex]) {
                cells[columnIndex].classList.remove('even-column', 'odd-column');
                if (visibleIndex % 2 === 0) {
                    cells[columnIndex].classList.add('even-column');
                } else {
                    cells[columnIndex].classList.add('odd-column');
                }
            }
        });
    });
}

// Export global functions
window.sortCriticColumnsByReviews = sortCriticColumnsByReviews;
window.updateCriticColumnVisibility = updateCriticColumnVisibility;
window.showPosterInCell = showPosterInCell;
window.hidePosterInCell = hidePosterInCell;
window.resetMovieCell = resetMovieCell;
window.addFillerColumns = addFillerColumns;
window.removeFillerColumns = removeFillerColumns;
