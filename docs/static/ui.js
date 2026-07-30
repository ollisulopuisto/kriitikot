// Kriitikon valinta - UI Components
// ==================================

/**
 * Päivitä suodatinpalkin korkeus CSS-muuttujaan.
 * Kirjoitetaan vain kun arvo muuttuu, jottei jokainen scroll-event aiheuta layoutia.
 */
let cachedFiltersHeight = -1;
function updateFiltersHeight() {
    const desktopFilters = document.querySelector('.desktop-filters');
    if (desktopFilters) {
        const height = desktopFilters.offsetHeight;
        if (height !== cachedFiltersHeight) {
            cachedFiltersHeight = height;
            document.documentElement.style.setProperty('--filters-height', height + 'px');
        }
        return height;
    }
    return 0;
}

/**
 * Fake sticky thead (koska position:sticky ei toimi overflow:n kanssa)
 */
function initStickyTableHeader() {
    const desktopFilters = document.querySelector('.desktop-filters');
    const thead = document.querySelector('thead');
    const tableWrapper = document.querySelector('.table-wrapper');
    const table = document.querySelector('table');
    
    if (!desktopFilters || !thead || !tableWrapper || !table) return;
    if (thead.dataset.stickyInitialized) return; // Prevent double initialization
    
    let theadClone = null;
    
    function syncColumnWidths() {
        if (!theadClone) return;

        const originalCells = thead.querySelectorAll('th');
        const clonedCells = theadClone.querySelectorAll('th');

        // Lukuvaihe ensin, kirjoitusvaihe erikseen — vuorottelu pakottaisi
        // selaimen laskemaan layoutin uudelleen joka solulle
        const sizes = Array.from(originalCells, cell => {
            const rect = cell.getBoundingClientRect();
            return {
                width: rect.width,
                height: cell.classList.contains('diagonal-sort-cell') ? rect.height : null
            };
        });

        sizes.forEach((size, index) => {
            const clone = clonedCells[index];
            if (!clone) return;
            clone.style.width = size.width + 'px';
            clone.style.minWidth = size.width + 'px';
            clone.style.maxWidth = size.width + 'px';
            if (size.height !== null) {
                clone.style.height = size.height + 'px';
                clone.style.minHeight = size.height + 'px';
                clone.style.maxHeight = size.height + 'px';
            }
        });
    }
    
    function handleScroll() {
        if (window.innerWidth <= 768) return; // Mobiilissa taulukko on piilossa

        const filtersHeight = updateFiltersHeight();
        const filterBottom = filtersHeight; // Otsikkoheader kiinnittyy fasetin alle
        const tableRect = tableWrapper.getBoundingClientRect();
        
        const shouldBeSticky = tableRect.top < filterBottom && 
                              tableRect.bottom > filterBottom + thead.offsetHeight;
        
        if (shouldBeSticky) {
            if (!theadClone) {
                const wrapper = document.createElement('div');
                wrapper.id = 'sticky-thead-wrapper';
                wrapper.style.position = 'fixed';
                wrapper.style.top = filterBottom + 'px';
                wrapper.style.left = tableRect.left + 'px';
                wrapper.style.width = tableRect.width + 'px';
                wrapper.style.zIndex = '500'; // Below desktop-filters (1000)
                wrapper.style.overflow = 'hidden';
                wrapper.style.boxShadow = '0 0.125rem 0.5rem rgba(0,0,0,0.1)';
                wrapper.style.borderRadius = '0.5rem 0.5rem 0 0';
                wrapper.style.background = '#f8f9fa';
                
                theadClone = document.createElement('table');
                theadClone.id = 'sticky-thead-clone';
                theadClone.style.borderCollapse = 'collapse';
                theadClone.style.margin = '0';
                theadClone.style.padding = '0';
                theadClone.style.background = '#f8f9fa';
                
                const clonedThead = thead.cloneNode(true);
                theadClone.appendChild(clonedThead);
                
                wrapper.appendChild(theadClone);
                document.body.appendChild(wrapper);
                
                theadClone.wrapperElement = wrapper;
                
                // Event delegation
                theadClone.addEventListener('click', function(e) {
                    const clickedElement = e.target.closest('th');
                    if (!clickedElement) return;
                    
                    const cells = Array.from(theadClone.querySelectorAll('th'));
                    const index = cells.indexOf(clickedElement);
                    
                    if (index !== -1) {
                        const originalCells = Array.from(thead.querySelectorAll('th'));
                        const originalCell = originalCells[index];
                        
                        // Jos kyseessä on kriitikon sarake, suodata sen mukaan
                        if (originalCell && originalCell.classList.contains('rating-cell')) {
                            window.filterByCritic(originalCell);
                        } else if (originalCell) {
                            // Muussa tapauksessa simuloi alkuperäistä klikkausta (esim. movie-col)
                            originalCell.click();
                        }
                    }
                });
                
                const sortAreas = theadClone.querySelectorAll('[id^="sort-"]');
                sortAreas.forEach(area => {
                    area.addEventListener('click', function(e) {
                        e.stopPropagation();
                        const originalArea = document.getElementById(this.id.replace('-clone', ''));
                        if (originalArea) {
                            originalArea.click();
                        }
                    });
                });
                
                thead.style.visibility = 'hidden';
                
                syncColumnWidths();
            }
            
            if (theadClone && theadClone.wrapperElement) {
                const wrapper = theadClone.wrapperElement;
                wrapper.style.top = filterBottom + 'px';
                wrapper.style.left = tableRect.left + 'px';
                wrapper.style.width = tableRect.width + 'px';
                
                const scrollLeft = tableWrapper.scrollLeft;
                const clonedCells = theadClone.querySelectorAll('th');
                clonedCells.forEach((cell, index) => {
                    if (index === 0) {
                        cell.style.position = 'sticky';
                        cell.style.left = '0';
                        cell.style.zIndex = '52';
                        cell.style.transform = 'none';
                    } else {
                        cell.style.transform = `translateX(-${scrollLeft}px)`;
                    }
                });
            }
        } else {
            if (theadClone) {
                if (theadClone.wrapperElement) {
                    theadClone.wrapperElement.remove();
                } else {
                    theadClone.remove();
                }
                theadClone = null;
                thead.style.visibility = 'visible';
            }
        }
    }

    /**
     * Päivitä sticky header (esim. lajittelun jälkeen)
     */
    function refreshStickyHeader() {
        if (theadClone) {
            if (theadClone.wrapperElement) {
                theadClone.wrapperElement.remove();
            } else {
                theadClone.remove();
            }
            theadClone = null;
            thead.style.visibility = 'visible';
            handleScroll();
        }
    }
    
    // rAF-tahdistus: enintään yksi käsittely per frame
    let scrollTicking = false;
    function onScroll() {
        if (scrollTicking) return;
        scrollTicking = true;
        requestAnimationFrame(() => {
            scrollTicking = false;
            handleScroll();
        });
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', () => {
        updateFiltersHeight();
        syncColumnWidths();
        handleScroll();
    });
    tableWrapper.addEventListener('scroll', onScroll, { passive: true });
    
    // Kuuntele lajittelun tapahtumia
    document.addEventListener('table-sorted', refreshStickyHeader);
    
    updateFiltersHeight();
    handleScroll();
    thead.dataset.stickyInitialized = 'true'; // Mark as initialized
}

/**
 * Mobile filter toggle
 */
function initMobileFilterToggle() {
    const toggleBtn = document.getElementById('mobile-filter-toggle');
    const mobileFilter = document.querySelector('.mobile-filter');
    const toggleText = toggleBtn?.querySelector('.toggle-text');
    
    if (!toggleBtn || !mobileFilter || toggleBtn.dataset.initialized) return;

    toggleBtn.addEventListener('click', function() {
        mobileFilter.classList.toggle('collapsed');
        
        if (toggleText) {
            toggleText.textContent = mobileFilter.classList.contains('collapsed') ? 'Hakuehdot' : 'Piilota';
        }
    });
    
    toggleBtn.dataset.initialized = 'true';
}

/**
 * Sticky horizontal scrollbar synchronization (desktop only)
 */
function initStickyScrollbar() {
    const tableWrapper = document.querySelector('.table-wrapper');
    const stickyScrollbar = document.querySelector('.sticky-scrollbar-container');
    const stickyScrollbarContent = document.querySelector('.sticky-scrollbar-content');

    if (!tableWrapper || !stickyScrollbar || !stickyScrollbarContent) return;
    if (tableWrapper.dataset.stickyScrollbarInitialized) return; // Prevent double initialization

    let syncingFromTable = false;
    let syncingFromSticky = false;

    function updateScrollbarWidth() {
        const table = tableWrapper.querySelector('table');
        if (table) {
            const tableWidth = table.scrollWidth;
            const wrapperWidth = tableWrapper.clientWidth;
            stickyScrollbarContent.style.width = tableWidth + 'px';

            if (tableWidth <= wrapperWidth) {
                stickyScrollbar.style.display = 'none';
            } else {
                stickyScrollbar.style.display = 'block';
            }
        }
    }

    // Kaksisuuntainen synkronointi ilman setTimeout-viivettä: lippu kulutetaan
    // vastapuolen scroll-eventissä, ja asetetaan vain jos arvo oikeasti muuttuu
    tableWrapper.addEventListener('scroll', function() {
        if (syncingFromSticky) { syncingFromSticky = false; return; }
        if (stickyScrollbar.scrollLeft !== tableWrapper.scrollLeft) {
            syncingFromTable = true;
            stickyScrollbar.scrollLeft = tableWrapper.scrollLeft;
        }
    }, { passive: true });

    stickyScrollbar.addEventListener('scroll', function() {
        if (syncingFromTable) { syncingFromTable = false; return; }
        if (tableWrapper.scrollLeft !== stickyScrollbar.scrollLeft) {
            syncingFromSticky = true;
            tableWrapper.scrollLeft = stickyScrollbar.scrollLeft;
        }
    }, { passive: true });

    updateScrollbarWidth();
    window.addEventListener('resize', updateScrollbarWidth);

    // Kootaan DOM-muutosten aiheuttamat päivitykset yhteen framea kohti —
    // suodatus kirjoittaa satoja style-attribuutteja kerralla
    let scrollbarUpdateQueued = false;
    const observer = new MutationObserver(() => {
        if (scrollbarUpdateQueued) return;
        scrollbarUpdateQueued = true;
        requestAnimationFrame(() => {
            scrollbarUpdateQueued = false;
            updateScrollbarWidth();
        });
    });
    observer.observe(tableWrapper, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'class']
    });
    tableWrapper.dataset.stickyScrollbarInitialized = 'true'; // Mark as initialized
}

/**
 * Tallenna alkuperäinen sarakkeiden määrä
 */
function initColumnCount() {
    const table = document.querySelector('table');
    if (table && window.originalVisibleColumns === 0) {
        const allHeaders = Array.from(table.querySelectorAll('thead th:not(.filler-column)'));
        window.originalVisibleColumns = allHeaders.filter(th => {
            const style = window.getComputedStyle(th);
            return style.display !== 'none';
        }).length;
    }
}

// Initialize all UI components
document.addEventListener('DOMContentLoaded', function() {
    initStickyTableHeader();
    initMobileFilterToggle();
    initStickyScrollbar();
    initColumnCount();
    
    // Varmista fassettien korkeuden päivitys kun layout on valmis
    setTimeout(updateFiltersHeight, 100);
});

// Export functions to window
window.updateFiltersHeight = updateFiltersHeight;
window.initStickyTableHeader = initStickyTableHeader;
window.refreshStickyHeader = function() {
    document.dispatchEvent(new CustomEvent('table-sorted'));
};
