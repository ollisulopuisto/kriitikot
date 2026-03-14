// Kriitikon valinta - Filter Functionality
// =========================================

/**
 * Arvioiden määrä -suodatin (desktop + mobile)
 */
function initReviewCountFilter() {
    const slider = document.getElementById('min-reviews-slider');
    const valueDisplay = document.getElementById('min-reviews-value');
    const valueDisplayMobile = document.getElementById('min-reviews-value-mobile');
    const table = document.querySelector('table');
    const mobileCards = document.querySelectorAll('.movie-card');

    if (!slider || !valueDisplay) return;
    if (slider.dataset.initialized) return; // Prevent double initialization

    // Laske jokaisen elokuvan arvioiden määrä
    const movieReviewCounts = new Map();

    // Desktop: Laske taulukon riveiltä
    if (table) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');

        rows.forEach(row => {
            const movieCell = row.querySelector('.movie-col');
            if (!movieCell) return;

            const movieTitle = movieCell.textContent.trim();
            const ratingCells = row.querySelectorAll('.rating-cell');

            let reviewCount = 0;
            ratingCells.forEach(cell => {
                const hasLink = cell.querySelector('a.rating-link');
                const hasStars = cell.querySelector('.rating-stars');
                const noRating = cell.querySelector('.no-rating');

                if (hasLink || hasStars || (noRating && !noRating.textContent.includes('–'))) {
                    reviewCount++;
                }
            });

            movieReviewCounts.set(movieTitle, reviewCount);
            row.dataset.reviewCount = reviewCount;
        });
    }

    // Mobile: Laske korteista
    mobileCards.forEach(card => {
        const movieTitle = card.dataset.movie;
        const reviewItems = card.querySelectorAll('.review-item');
        const reviewCount = reviewItems.length;

        movieReviewCounts.set(movieTitle, reviewCount);
        card.dataset.reviewCount = reviewCount;
    });

    const reviewValueMapping = {
        1: 1,
        2: 2,
        3: 4,
        4: 6,
        5: 8
    };

    function filterByReviewCount(mappedMinCount) {
        let hiddenCount = 0;

        // Desktop: Piilota rivit
        if (table) {
            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');

            rows.forEach(row => {
                const count = parseInt(row.dataset.reviewCount || 0);
                if (count < mappedMinCount) {
                    row.style.display = 'none';
                    row.dataset.reviewCountFiltered = 'true';
                    hiddenCount++;
                } else {
                    delete row.dataset.reviewCountFiltered;
                    if (!row.dataset.starFiltered) {
                        row.style.display = '';
                    }
                }
            });
        }

        // Mobile: Piilota kortit
        mobileCards.forEach(card => {
            const count = parseInt(card.dataset.reviewCount || 0);
            if (count < mappedMinCount) {
                card.style.display = 'none';
                card.dataset.reviewCountFiltered = 'true';
                hiddenCount++;
            } else {
                delete card.dataset.reviewCountFiltered;
                if (!card.dataset.starFiltered) {
                    card.style.display = '';
                }
            }
        });

        if (mappedMinCount > 1) {
            if (window.showResetButton) window.showResetButton();
        }

        if (typeof updateCriticColumnVisibility === 'function') {
            updateCriticColumnVisibility();
        }

        return hiddenCount;
    }

    function updateReviewWord(actualCountValue) {
        const reviewWord = document.getElementById('review-word');
        const word = actualCountValue === 1 ? 'arvostelu' : 'arvostelua';
        if (reviewWord) reviewWord.textContent = word;
    }

    // Desktop slider
    slider.addEventListener('input', function () {
        const sliderPos = parseInt(this.value);
        const mappedValue = reviewValueMapping[sliderPos] || sliderPos;
        
        valueDisplay.textContent = mappedValue;
        updateReviewWord(mappedValue);
        
        if (valueDisplayMobile) {
            valueDisplayMobile.textContent = mappedValue;
        }
        
        filterByReviewCount(mappedValue);
    });
    slider.dataset.initialized = 'true';

    // Mobile stepper buttons
    const reviewsMinusBtn = document.getElementById('reviews-minus-mobile');
    const reviewsPlusBtn = document.getElementById('reviews-plus-mobile');

    if (reviewsMinusBtn && reviewsPlusBtn && valueDisplayMobile && !reviewsMinusBtn.dataset.initialized) {
        let currentSliderPos = 1;

        const updateReviewStepper = (newSliderPos, shouldFilter = true) => {
            currentSliderPos = Math.max(1, Math.min(5, newSliderPos));
            const mappedValue = reviewValueMapping[currentSliderPos] || currentSliderPos;
            
            valueDisplayMobile.textContent = mappedValue;
            valueDisplay.textContent = mappedValue;
            slider.value = currentSliderPos;
            updateReviewWord(mappedValue);

            if (shouldFilter) {
                filterByReviewCount(mappedValue);
            }

            reviewsMinusBtn.disabled = currentSliderPos <= 1;
            reviewsPlusBtn.disabled = currentSliderPos >= 5;
        };

        reviewsMinusBtn.addEventListener('click', () => updateReviewStepper(currentSliderPos - 1));
        reviewsPlusBtn.addEventListener('click', () => updateReviewStepper(currentSliderPos + 1));

        updateReviewStepper(1, false);
        reviewsMinusBtn.dataset.initialized = 'true';
    }
}

/**
 * Tähtisuodatin
 */
function initStarFilter() {
    const starSlider = document.getElementById('star-filter-slider');
    const starValueDisplay = document.getElementById('star-filter-value');
    const starValueDisplayMobile = document.getElementById('star-filter-value-mobile');

    if (!starSlider || !starValueDisplay) return;
    if (starSlider.dataset.initialized) return; // Prevent double initialization
    
    function updateStarLabel(value) {
        const labels = {
            1: 'Vähintään ★',
            2: 'Vähintään ★★',
            3: 'Vähintään ★★★',
            4: 'Vähintään ★★★★',
            5: 'Vähintään ★★★★★'
        };
        const mobileLabels = {
            1: '★',
            2: '★★',
            3: '★★★',
            4: '★★★★',
            5: '★★★★★'
        };
        const label = labels[value] || 'Vähintään ★';
        const mobileLabel = mobileLabels[value] || '★';
        if (starValueDisplay) starValueDisplay.innerHTML = label;
        if (starValueDisplayMobile) starValueDisplayMobile.innerHTML = mobileLabel;
    }

    function filterByStars(stars) {
        console.log('🔍 filterByStars starting. Target stars >=', stars);

        const table = document.querySelector('table');
        const allCards = document.querySelectorAll('.movie-card');

        // Jos stars on 1, poista tähtifiltteri kokonaan
        if (stars === 1) {
            console.log('✅ Stars = 1, resetting all dimming');

            // Desktop
            if (table) {
                const tbody = table.querySelector('tbody');
                const allRows = tbody.querySelectorAll('tr');

                allRows.forEach(row => {
                    row.dataset.starFiltered = 'false';
                    row.querySelectorAll('.rating-cell').forEach(cell => {
                        cell.classList.remove('dimmed');
                        const pills = cell.querySelectorAll('.rating-pill');
                        pills.forEach(p => p.classList.remove('dimmed'));
                    });

                    // Tarkista muut suodattimet ennen näyttämistä
                    const isCountFiltered = row.dataset.reviewCountFiltered === 'true';
                    const isPubFiltered = row.style.display === 'none' && !row.dataset.starFiltered; // Alkeellinen tsekkaus
                    
                    if (!isCountFiltered) {
                        row.style.display = '';
                    }
                });
            }

            // Mobile
            allCards.forEach(card => {
                card.dataset.starFiltered = 'false';
                const isCountFiltered = card.dataset.reviewCountFiltered === 'true';
                if (!isCountFiltered) card.style.display = '';

                card.querySelectorAll('.review-item').forEach(item => {
                    item.classList.remove('dimmed');
                    const pill = item.querySelector('.rating-pill');
                    if (pill) pill.classList.remove('dimmed');
                });
            });

            if (typeof updateCriticColumnVisibility === 'function') updateCriticColumnVisibility();
            return;
        }

        // Desktop: Filtteröi (stars > 1)
        if (table) {
            const tbody = table.querySelector('tbody');
            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');

            allRows.forEach(row => {
                const ratingCells = row.querySelectorAll('.rating-cell');
                let hasAtLeastOneMatchingReview = false;

                ratingCells.forEach(cell => {
                    // Solussa voi olla useita arvosteluja (jos useita julkaisu-tagit käytössä)
                    // tai vain yksi.
                    const pills = cell.querySelectorAll('.rating-pill');
                    let cellHasMatch = false;

                    pills.forEach(pill => {
                        const starText = pill.querySelector('.rating-stars')?.textContent || pill.textContent;
                        const starCount = (starText.match(/★/g) || []).length;
                        
                        if (starCount >= stars) {
                            hasAtLeastOneMatchingReview = true;
                            cellHasMatch = true;
                            pill.classList.remove('dimmed');
                        } else {
                            pill.classList.add('dimmed');
                        }
                    });

                    // Jos solussa ei ole yhtään matchia, koko solu voidaan himmentää 
                    // (mutta vain jos siellä on jotain arvioita)
                    if (pills.length > 0 && !cellHasMatch) {
                        cell.classList.add('dimmed');
                    } else {
                        cell.classList.remove('dimmed');
                    }
                });

                // 1. Piilota rivi jos EI YHTÄÄN arvostelua >= kynnys
                if (hasAtLeastOneMatchingReview) {
                    row.style.display = '';
                    row.dataset.starFiltered = 'false';
                } else {
                    row.style.display = 'none';
                    row.dataset.starFiltered = 'true';
                }
            });
        }

        // Mobile: Filtteröi (stars > 1)
        allCards.forEach(card => {
            const reviews = card.querySelectorAll('.review-item');
            let hasAtLeastOneMatchingReview = false;

            reviews.forEach(item => {
                const ratingElem = item.querySelector('.review-rating');
                const ratingText = ratingElem ? ratingElem.textContent : '';
                const starCount = (ratingText.match(/★/g) || []).length;

                if (starCount >= stars) {
                    hasAtLeastOneMatchingReview = true;
                    item.classList.remove('dimmed');
                    const pill = item.querySelector('.rating-pill');
                    if (pill) pill.classList.remove('dimmed');
                } else {
                    item.classList.add('dimmed');
                    const pill = item.querySelector('.rating-pill');
                    if (pill) pill.classList.add('dimmed');
                }
            });

            if (hasAtLeastOneMatchingReview) {
                card.style.display = '';
                card.dataset.starFiltered = 'false';
            } else {
                card.style.display = 'none';
                card.dataset.starFiltered = 'true';
            }
        });

        if (typeof updateCriticColumnVisibility === 'function') {
            updateCriticColumnVisibility();
        }
    }

    // Desktop slider
    starSlider.addEventListener('input', function () {
        const value = parseInt(this.value);
        console.log('🌟 Star slider changed to:', value);
        updateStarLabel(value);
        filterByStars(value);
    });
    starSlider.dataset.initialized = 'true';

    // Mobile stepper buttons
    const starsMinusBtn = document.getElementById('stars-minus-mobile');
    const starsPlusBtn = document.getElementById('stars-plus-mobile');

    if (starsMinusBtn && starsPlusBtn && !starsMinusBtn.dataset.initialized) {
        let currentValue = 1;

        const updateStarStepper = (newValue, shouldFilter = true) => {
            currentValue = Math.max(1, Math.min(5, newValue));

            updateStarLabel(currentValue);
            starSlider.value = currentValue;

            if (shouldFilter) {
                filterByStars(currentValue);
            }

            starsMinusBtn.disabled = (currentValue <= 1);
            starsPlusBtn.disabled = (currentValue >= 5);
        };

        starsMinusBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (!this.disabled) {
                updateStarStepper(currentValue - 1);
            }
        });

        starsPlusBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (!this.disabled) {
                updateStarStepper(currentValue + 1);
            }
        });

        updateStarStepper(1, false);
        starsMinusBtn.dataset.initialized = 'true';
    }

    // Export functions to window for testing or external access
    window.filterByStars = filterByStars;
}
window.initStarFilter = initStarFilter;

/**
 * Reset-nappi
 */
function initResetButton() {
    const resetButtonDesktop = document.getElementById('reset-filters-desktop');
    const resetButtonMobile = document.getElementById('reset-filters-mobile');

    if (!resetButtonDesktop || resetButtonDesktop.dataset.initialized) return;

    function showResetButton() {
        if (resetButtonDesktop) resetButtonDesktop.style.display = 'inline-block';
        if (resetButtonMobile) resetButtonMobile.style.display = 'flex';
    }

    function hideResetButton() {
        if (resetButtonDesktop) resetButtonDesktop.style.display = 'none';
        if (resetButtonMobile) resetButtonMobile.style.display = 'none';
    }

    function resetAllFilters() {
        // Nollaa suodattimet
        const slider = document.getElementById('min-reviews-slider');
        const starSlider = document.getElementById('star-filter-slider');

        if (slider) slider.value = 1;
        if (starSlider) starSlider.value = 1;

        const valueDisplay = document.getElementById('min-reviews-value');
        const valueDisplayMobile = document.getElementById('min-reviews-value-mobile');
        const starValueDisplay = document.getElementById('star-filter-value');
        const starValueDisplayMobile = document.getElementById('star-filter-value-mobile');

        if (valueDisplay) valueDisplay.textContent = '1';
        if (valueDisplayMobile) valueDisplayMobile.textContent = '1';
        if (starValueDisplay) starValueDisplay.innerHTML = 'Vähintään ★';
        if (starValueDisplayMobile) starValueDisplayMobile.innerHTML = '★';

        const criticFilterValue = document.getElementById('critic-filter-value-mobile');
        if (criticFilterValue) criticFilterValue.textContent = 'Kaikki';

        const reviewWord = document.getElementById('review-word');
        if (reviewWord) reviewWord.textContent = 'arvostelu';

        // Nollaa suosikit-kytkimet
        const favToggleDesktop = document.getElementById('favorites-toggle-desktop');
        const favToggleMobile = document.getElementById('favorites-toggle-mobile');
        if (favToggleDesktop) favToggleDesktop.checked = false;
        if (favToggleMobile) favToggleMobile.checked = false;

        // Reset mobile stepper buttons
        const reviewsMinusBtn = document.getElementById('reviews-minus-mobile');
        const reviewsPlusBtn = document.getElementById('reviews-plus-mobile');
        const starsMinusBtn = document.getElementById('stars-minus-mobile');
        const starsPlusBtn = document.getElementById('stars-plus-mobile');

        if (reviewsMinusBtn) reviewsMinusBtn.disabled = true;
        if (reviewsPlusBtn) reviewsPlusBtn.disabled = false;
        if (starsMinusBtn) starsMinusBtn.disabled = true;
        if (starsPlusBtn) starsPlusBtn.disabled = false;

        // Palauta skrollaus
        const tableWrapper = document.querySelector('.table-wrapper');
        if (tableWrapper) {
            const originalScrollBehavior = tableWrapper.style.scrollBehavior;
            tableWrapper.style.scrollBehavior = 'auto';
            tableWrapper.scrollLeft = window.savedScrollLeft || 0;
            setTimeout(() => {
                tableWrapper.style.scrollBehavior = originalScrollBehavior;
            }, 50);
        }

        // Poista täytesarake
        if (window.removeFillerColumns) window.removeFillerColumns();

        // Nollaa leveydet
        window.originalTableWidth = 0;
        window.originalVisibleColumns = 0;

        // Desktop: Poista kaikki filtterit ja himmennykset
        const table = document.querySelector('table');
        if (table) {
            const tbody = table.querySelector('tbody');
            const allRows = tbody.querySelectorAll('tr:not(.poster-row)');
            const allCriticHeaders = table.querySelectorAll('thead th.rating-cell');

            // Poista poster-rivit
            const posterRows = tbody.querySelectorAll('.poster-row');
            posterRows.forEach(row => row.remove());

            // Näytä kaikki rivit
            allRows.forEach(row => {
                row.style.display = '';
                row.classList.remove('dimmed');
                delete row.dataset.filtered;
                delete row.dataset.starFiltered;
                delete row.dataset.reviewCountFiltered;
                const movieCell = row.querySelector('.movie-col');
                if (movieCell) {
                    movieCell.classList.remove('selected');
                    if (window.resetMovieCell) window.resetMovieCell(movieCell);
                }
            });

            // Näytä kaikki sarakkeet
            allCriticHeaders.forEach((header, idx) => {
                header.style.display = '';
                header.classList.remove('dimmed');
                header.classList.remove('filter-hidden');
                delete header.dataset.highlighted;
                delete header.dataset.filtered;
                header.style.backgroundColor = '';
                header.classList.remove('selected');

                tbody.querySelectorAll('tr').forEach(row => {
                    const cells = row.querySelectorAll('.rating-cell');
                    if (cells[idx]) {
                        cells[idx].style.display = '';
                        cells[idx].classList.remove('dimmed');
                        cells[idx].classList.remove('filter-hidden');
                        const pill = cells[idx].querySelector('.rating-pill');
                        if (pill) pill.classList.remove('dimmed');
                    }
                });
            });

            allRows.forEach(row => {
                row.querySelectorAll('.rating-cell').forEach(cell => {
                    cell.style.display = '';
                    cell.classList.remove('dimmed');
                    cell.classList.remove('filter-hidden');
                    const pill = cell.querySelector('.rating-pill');
                    if (pill) pill.classList.remove('dimmed');
                });
            });
        }

        // Mobile: Poista kaikki filtterit
        const allCards = document.querySelectorAll('.movie-card');
        const allReviewItems = document.querySelectorAll('.review-item');

        allCards.forEach(card => {
            card.style.display = '';
            delete card.dataset.filtered;
            delete card.dataset.starFiltered;
            delete card.dataset.reviewCountFiltered;
        });

        allReviewItems.forEach(item => {
            item.style.display = '';
            item.classList.remove('dimmed');
            const area = item.querySelector('.review-critic');
            const name = item.querySelector('.review-critic-name');
            if (area && name) {
                name.classList.remove('selected');
                delete area.dataset.filtered;
            }
        });

        // Footer: Poista korostukset
        const ratingFilters = document.querySelectorAll('.filter-rating');
        ratingFilters.forEach(filter => {
            filter.style.backgroundColor = '';
            filter.style.fontWeight = '';
        });

        const publicationFilters = document.querySelectorAll('.filter-publication');
        publicationFilters.forEach(filter => {
            filter.classList.remove('active');
            filter.style.backgroundColor = '';
            filter.style.fontWeight = '';
        });

        // Päivitä sarakkeiden väritys
        if (typeof updateCriticColumnVisibility === 'function') {
            updateCriticColumnVisibility();
        }

        hideResetButton();
    }

    function isAnyFilterActive() {
        return (resetButtonDesktop && resetButtonDesktop.style.display !== 'none') ||
            (resetButtonMobile && resetButtonMobile.style.display !== 'none');
    }

    // Click-handlerit
    resetButtonDesktop.addEventListener('click', resetAllFilters);

    // Tee otsikosta klikattava reset-nappi
    const headerTitle = document.querySelector('h1');
    if (headerTitle) {
        headerTitle.style.cursor = 'pointer';
        headerTitle.title = 'Klikkaa nollataksesi kaikki hakufasetit';
        headerTitle.addEventListener('click', function () {
            resetAllFilters();
        });
    }

    // Export funktiot
    window.showResetButton = showResetButton;
    window.resetAllFilters = resetAllFilters;
    window.isAnyFilterActive = isAnyFilterActive;
    
    resetButtonDesktop.dataset.initialized = 'true';
}

/**
 * Suosikkikriitikot
 */
function initFavoriteFilter() {
    // 1. Load favorites from localStorage
    let favorites = [];
    try {
        favorites = JSON.parse(localStorage.getItem('kriitikot_favorites') || '[]');
    } catch (e) {
        console.error('Failed to load favorites', e);
    }

    // 2. Setup Toggle Functionality
    window.toggleFavorite = function (criticId, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        const index = favorites.indexOf(criticId);
        if (index === -1) {
            favorites.push(criticId);
        } else {
            favorites.splice(index, 1);
        }

        try {
            localStorage.setItem('kriitikot_favorites', JSON.stringify(favorites));
        } catch (e) {
            console.error('Failed to save favorites', e);
        }

        updateHeartIcons();

        // Jos suosikkifiltteri on päällä, päivitä näkymä heti
        const favToggleDesktop = document.getElementById('favorites-toggle-desktop');
        const favToggleMobile = document.getElementById('favorites-toggle-mobile');
        if ((favToggleDesktop && favToggleDesktop.checked) || (favToggleMobile && favToggleMobile.checked)) {
            filterByFavorites(true);
        }
    };

    // 3. Update UI Icons
    function updateHeartIcons() {
        // Desktop Headers
        document.querySelectorAll('th.rating-cell').forEach(th => {
            const criticId = th.dataset.criticId;
            let heart = th.querySelector('.heart-icon');

            if (!heart) {
                heart = document.createElement('span');
                heart.className = 'heart-icon';
                heart.innerHTML = '♥';
                heart.title = 'Merkitse suosikkikriitikoksi';
                heart.onclick = (e) => window.toggleFavorite(criticId, e);

                // Insert into critic-bottom-row
                const bottomRow = th.querySelector('.critic-bottom-row');
                if (bottomRow) {
                    bottomRow.appendChild(heart);
                } else {
                    th.appendChild(heart);
                }
            }

            if (favorites.includes(criticId)) {
                heart.classList.add('active');
                heart.innerHTML = '❤️';
            } else {
                heart.classList.remove('active');
                heart.innerHTML = '♡';
            }
        });

        // Mobile Reviews
        document.querySelectorAll('.review-item').forEach(item => {
            const criticId = item.dataset.critic;
            const criticNameSpan = item.querySelector('.review-critic-name');

            if (criticNameSpan) {
                let heart = item.querySelector('.heart-icon');
                if (!heart) {
                    heart = document.createElement('span');
                    heart.className = 'heart-icon mobile-heart';
                    heart.innerHTML = '♥';
                    heart.onclick = (e) => window.toggleFavorite(criticId, e);
                    criticNameSpan.parentNode.insertBefore(heart, criticNameSpan.nextSibling);
                }

                if (favorites.includes(criticId)) {
                    heart.classList.add('active');
                    heart.innerHTML = '❤️';
                } else {
                    heart.classList.remove('active');
                    heart.innerHTML = '♡';
                }
            }
        });
    }

    // 4. Filtering Logic
    window.filterByFavorites = function (enabled) {
        // Desktop
        const table = document.querySelector('table');
        if (table) {
            if (typeof updateCriticColumnVisibility === 'function') {
                updateCriticColumnVisibility();
            }
        }

        // Mobile
        const allCards = document.querySelectorAll('.movie-card');
        allCards.forEach(card => {
            const reviews = card.querySelectorAll('.review-item');
            let hasVisibleReviews = false;

            reviews.forEach(review => {
                const criticId = review.dataset.critic;
                if (enabled && !favorites.includes(criticId)) {
                    review.style.display = 'none';
                    review.dataset.favoriteFiltered = 'true';
                } else {
                    delete review.dataset.favoriteFiltered;
                    // Palauta näkyviin vain jos ei muita filttereitä (tähdet)
                    if (!review.dataset.starFiltered) {
                        review.style.display = '';
                        hasVisibleReviews = true;
                    }
                }
            });

            if (enabled && !hasVisibleReviews) {
                card.style.display = 'none';
            } else if (!enabled) {
                if (!card.dataset.starFiltered && !card.dataset.reviewCountFiltered) {
                    card.style.display = '';
                }
            }
        });

        if (enabled) {
            if (window.showResetButton) window.showResetButton();
        }
    };

    // Toggle Event Listeners
    const favToggleDesktop = document.getElementById('favorites-toggle-desktop');
    const favToggleMobile = document.getElementById('favorites-toggle-mobile');

    if (favToggleDesktop && !favToggleDesktop.dataset.initialized) {
        function handleToggleChange(e) {
            const checked = e.target.checked;
            if (favToggleDesktop) favToggleDesktop.checked = checked;
            if (favToggleMobile) favToggleMobile.checked = checked;

            filterByFavorites(checked);
        }

        favToggleDesktop.addEventListener('change', handleToggleChange);
        if (favToggleMobile) favToggleMobile.addEventListener('change', handleToggleChange);
        
        favToggleDesktop.dataset.initialized = 'true';
    }

    // Initial render
    updateHeartIcons();

    // Export helper to check if a critic is favorite (for app.js)
    window.isFavoriteCritic = function (criticId) {
        return favorites.includes(criticId);
    };

    // Export toggle status helper
    window.isFavoritesFilterActive = function () {
        return (favToggleDesktop && favToggleDesktop.checked) ||
            (favToggleMobile && favToggleMobile.checked);
    };
}

// Initialize all filters
document.addEventListener('DOMContentLoaded', function () {
    initReviewCountFilter();
    initStarFilter();
    initResetButton();
    initFavoriteFilter();
});
