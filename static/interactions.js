// Kriitikon valinta - Sorting and Click Handlers
// ===============================================

/**
 * Ylänurkka: Aakkosta elokuvat ja kriitikot
 */
function initSorting() {
    const table = document.querySelector('table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const sortMovieArea = document.getElementById('sort-movie-area');
    const sortCriticArea = document.getElementById('sort-critic-area');
    let sortAscending = true;
    let sortCriticAscending = true;
    
    // Elokuvanimi sort
    function sortMovies() {
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
        
        sortMovieArea.classList.add('active');
        setTimeout(() => sortMovieArea.classList.remove('active'), 300);
    }
    
    if (sortMovieArea) {
        sortMovieArea.addEventListener('click', function(e) {
            e.stopPropagation();
            sortMovies();
        });
        sortMovieArea.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                sortMovies();
            }
        });
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
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td.rating-cell'));
            critics.forEach((c, newIdx) => {
                row.appendChild(cells[c.idx]);
            });
        });
        
        sortCriticAscending = !sortCriticAscending;
        
        sortCriticArea.classList.add('active');
        setTimeout(() => sortCriticArea.classList.remove('active'), 300);
    }
    
    if (sortCriticArea) {
        sortCriticArea.addEventListener('click', function(e) {
            e.stopPropagation();
            sortCritics();
        });
        sortCriticArea.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                sortCritics();
            }
        });
    }
    
    // Mobiili: Aakkosta elokuvakortit
    const mobileSortButton = document.getElementById('mobile-sort');
    const mobileCardsContainer = document.querySelector('.mobile-cards');
    if (mobileSortButton && mobileCardsContainer) {
        let mobileSortAscending = true;
        mobileSortButton.addEventListener('click', function() {
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
            mobileSortButton.innerHTML = (mobileSortAscending ? '▼' : '▲') + ' Aakkosta elokuvat';
        });
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
    
    tbody.querySelectorAll('.movie-col').forEach((movieCell) => {
        movieCell.style.cursor = 'pointer';
        movieCell.title = 'Klikkaa korostaaksesi tämän elokuvan arvostelut';
        
        movieCell.addEventListener('click', function() {
            const row = movieCell.parentElement;
            
            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();
            
            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }
            
            // Poista vanha poster-rivi
            const oldPosterRow = tbody.querySelector('.poster-row');
            if (oldPosterRow) oldPosterRow.remove();
            
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
                    letterboxdLink.title = 'Katso Letterboxd:ssä';
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
    });
}

/**
 * Kriitikon nimi click handler
 */
function initCriticClickHandlers() {
    const table = document.querySelector('table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const criticHeaders = table.querySelectorAll('thead th.rating-cell');
    
    criticHeaders.forEach((criticHeader) => {
        criticHeader.style.cursor = 'pointer';
        criticHeader.title = 'Klikkaa piilottaaksesi elokuvat, joilla ei ole arvosteluja';
        
        criticHeader.addEventListener('click', function() {
            const isAnyFilterActive = window.isAnyFilterActive && window.isAnyFilterActive();
            
            if (isAnyFilterActive) {
                if (window.resetAllFilters) window.resetAllFilters();
                return;
            }
            
            const rows = tbody.querySelectorAll('tr');
            const allCriticHeaders = table.querySelectorAll('thead th.rating-cell');
            const colIndex = Array.prototype.indexOf.call(allCriticHeaders, criticHeader);
            
            if (!window.originalTableWidth) {
                window.originalTableWidth = table.offsetWidth;
            }
            
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
            
            const visibleRows = [];
            
            rows.forEach(row => {
                const ratingCell = row.querySelectorAll('.rating-cell')[colIndex];
                const hasStars = ratingCell.querySelector('.rating-stars');
                
                if (!hasStars) {
                    row.classList.add('dimmed');
                    setTimeout(() => {
                        if (row.classList.contains('dimmed')) {
                            row.style.display = 'none';
                        }
                    }, 150);
                } else {
                    visibleRows.push(row);
                }
            });
            
            // Himmennä muut sarakkeet
            allCriticHeaders.forEach((header, idx) => {
                if (idx !== colIndex) {
                    header.classList.add('dimmed');
                    setTimeout(() => {
                        if (header.classList.contains('dimmed')) {
                            header.style.display = 'none';
                        }
                    }, 150);
                    
                    tbody.querySelectorAll('tr').forEach(row => {
                        if (!row.classList.contains('dimmed')) {
                            const cell = row.querySelectorAll('.rating-cell')[idx];
                            cell.classList.add('dimmed');
                            setTimeout(() => {
                                if (cell.classList.contains('dimmed')) {
                                    cell.style.display = 'none';
                                }
                            }, 150);
                        }
                    });
                }
            });
            
            // Piilota sarakkeet ilman arvosteluja
            allCriticHeaders.forEach((header, idx) => {
                if (idx === colIndex) return;
                
                let hasAnyReview = false;
                
                visibleRows.forEach(row => {
                    const cell = row.querySelectorAll('.rating-cell')[idx];
                    if (cell) {
                        const hasLink = cell.querySelector('a.rating-link');
                        const hasStars = cell.querySelector('.rating-stars');
                        const noRating = cell.querySelector('.no-rating');
                        const isEmpty = noRating && noRating.textContent.trim() === '–';
                        
                        if ((hasLink || hasStars) && !isEmpty) {
                            hasAnyReview = true;
                        }
                    }
                });
                
                if (!hasAnyReview) {
                    header.classList.add('filter-hidden');
                    
                    tbody.querySelectorAll('tr').forEach(row => {
                        const cells = row.querySelectorAll('.rating-cell');
                        if (cells[idx]) {
                            cells[idx].classList.add('filter-hidden');
                        }
                    });
                }
            });
            
            criticHeader.dataset.filtered = 'true';
            criticHeader.style.backgroundColor = 'rgba(139, 92, 246, 0.15)';
            criticHeader.classList.add('selected');
            
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
    });
}

/**
 * Mobile: Kriitikon nimi-alue click handler
 */
function initMobileCriticClickHandlers() {
    const reviewItems = document.querySelectorAll('.review-item');
    
    reviewItems.forEach(reviewItem => {
        const criticArea = reviewItem.querySelector('.review-critic');
        if (!criticArea) return;
        
        const criticName = reviewItem.querySelector('.review-critic-name');
        
        criticArea.style.cursor = 'pointer';
        criticArea.style.userSelect = 'none';
        criticArea.title = 'Klikkaa nähdäksesi vain tämän kriitikon arvostelut';
        
        criticArea.addEventListener('click', function(e) {
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
    });
}

/**
 * Footer: Tähtijakauma click handlers
 */
function initRatingFilterClickHandlers() {
    const ratingFilters = document.querySelectorAll('.filter-rating');
    ratingFilters.forEach(ratingFilter => {
        ratingFilter.addEventListener('click', function(e) {
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
                    } else {
                        item.style.display = 'none';
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
                            }
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
    });
}

/**
 * Footer: Julkaisut click handlers
 */
function initPublicationFilterClickHandlers() {
    const publicationFilters = document.querySelectorAll('.filter-publication');
    let activePublications = [];

    publicationFilters.forEach(pubFilter => {
        pubFilter.addEventListener('click', function(e) {
            e.preventDefault();
            
            const selectedPub = this.dataset.publication;
            const index = activePublications.indexOf(selectedPub);

            if (index > -1) {
                activePublications.splice(index, 1);
                this.style.backgroundColor = '';
                this.style.fontWeight = '';
            } else {
                activePublications.push(selectedPub);
                this.style.backgroundColor = '#f0e6ff';
                this.style.fontWeight = 'bold';
            }

            applyPublicationFilter(activePublications);

            if (activePublications.length > 0) {
                if (window.showResetButton) window.showResetButton();
            }
        });
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
            const thead = table.querySelector('thead');
            const tbody = table.querySelector('tbody');
            const headerCells = thead.querySelectorAll('th.rating-cell');
            const allRows = tbody.querySelectorAll('tr');

            headerCells.forEach((th, index) => {
                const mediaSpan = th.querySelector('.critic-media');
                const criticPublications = mediaSpan ? mediaSpan.textContent.trim().split(', ') : [];
                const isVisible = noFilter || publications.some(pub => criticPublications.includes(pub));
                
                const displayStyle = isVisible ? '' : 'none';
                th.style.display = displayStyle;
                allRows.forEach(row => {
                    const cells = row.querySelectorAll('td.rating-cell');
                    if (cells[index]) {
                        cells[index].style.display = displayStyle;
                    }
                });
            });

            allRows.forEach(row => {
                const ratingCells = row.querySelectorAll('.rating-cell');
                let hasVisibleRating = false;
                
                ratingCells.forEach(cell => {
                    if (cell.style.display !== 'none') {
                        const ratingLink = cell.querySelector('.rating-link');
                        const noRating = cell.querySelector('.no-rating');
                        if (ratingLink || (cell.textContent.trim() !== '' && (!noRating || cell.textContent.trim() !== '–'))) {
                            hasVisibleRating = true;
                        }
                    }
                });
                
                if (noFilter) {
                    row.style.display = '';
                } else {
                    row.style.display = hasVisibleRating ? '' : 'none';
                }
            });

            if (typeof updateCriticColumnVisibility === 'function') {
                setTimeout(() => {
                    updateCriticColumnVisibility();
                }, 200);
            }
            
            setTimeout(() => {
                if (window.removeFillerColumns) window.removeFillerColumns();
                if (window.addFillerColumns) window.addFillerColumns();
            }, 250);
        }
    }
}

// Initialize all click handlers
document.addEventListener('DOMContentLoaded', function() {
    initSorting();
    initMovieClickHandlers();
    initCriticClickHandlers();
    initMobileCriticClickHandlers();
    initRatingFilterClickHandlers();
    initPublicationFilterClickHandlers();
});
