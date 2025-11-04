// Kriitikon valinta - UI Components
// ==================================

/**
 * Fake sticky thead (koska position:sticky ei toimi overflow:n kanssa)
 */
function initStickyTableHeader() {
    const desktopFilters = document.querySelector('.desktop-filters');
    const thead = document.querySelector('thead');
    const tableWrapper = document.querySelector('.table-wrapper');
    const table = document.querySelector('table');
    
    if (!desktopFilters || !thead || !tableWrapper || !table) return;
    
    let theadClone = null;
    
    function syncColumnWidths() {
        if (!theadClone) return;
        
        const originalCells = thead.querySelectorAll('th');
        const clonedCells = theadClone.querySelectorAll('th');
        
        originalCells.forEach((cell, index) => {
            if (clonedCells[index]) {
                const width = cell.getBoundingClientRect().width;
                
                clonedCells[index].style.width = width + 'px';
                clonedCells[index].style.minWidth = width + 'px';
                clonedCells[index].style.maxWidth = width + 'px';
                
                if (cell.classList.contains('diagonal-sort-cell')) {
                    const height = cell.getBoundingClientRect().height;
                    clonedCells[index].style.height = height + 'px';
                    clonedCells[index].style.minHeight = height + 'px';
                    clonedCells[index].style.maxHeight = height + 'px';
                }
            }
        });
    }
    
    function handleScroll() {
        const filterBottom = desktopFilters.getBoundingClientRect().bottom;
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
                wrapper.style.zIndex = '50';
                wrapper.style.overflow = 'hidden';
                wrapper.style.boxShadow = '0 0.125rem 0.5rem rgba(0,0,0,0.1)';
                wrapper.style.borderRadius = '0.5rem 0.5rem 0 0';
                wrapper.style.background = '#f8f9fa';
                
                const stickyFade = document.createElement('div');
                stickyFade.className = 'scroll-fade-indicator-sticky';
                wrapper.appendChild(stickyFade);
                
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
                        
                        if (originalCell) {
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
                
                const clonedCells = theadClone.querySelectorAll('th');
                clonedCells.forEach((cell, index) => {
                    if (index === 0) {
                        cell.style.position = 'sticky';
                        cell.style.left = '0';
                        cell.style.zIndex = '52';
                        cell.style.transform = 'none';
                    } else {
                        cell.style.transform = `translateX(-${tableWrapper.scrollLeft}px)`;
                    }
                });
                
                syncColumnWidths();
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
    
    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', () => {
        syncColumnWidths();
        handleScroll();
    });
    tableWrapper.addEventListener('scroll', handleScroll);
    
    handleScroll();
}

/**
 * Mobile filter toggle
 */
function initMobileFilterToggle() {
    const toggleBtn = document.getElementById('mobile-filter-toggle');
    const mobileFilter = document.querySelector('.mobile-filter');
    const toggleText = toggleBtn?.querySelector('.toggle-text');
    const resetButtonMobile = document.getElementById('reset-filters-mobile');
    
    function updateResetButtonPosition() {
        if (mobileFilter && resetButtonMobile) {
            const filterHeight = mobileFilter.offsetHeight;
            const filterTop = parseFloat(window.getComputedStyle(mobileFilter).top);
            
            resetButtonMobile.style.top = (filterTop + filterHeight + 8) + 'px';
        }
    }
    
    if (toggleBtn && mobileFilter) {
        toggleBtn.addEventListener('click', function() {
            mobileFilter.classList.toggle('collapsed');
            
            if (mobileFilter.classList.contains('collapsed')) {
                toggleText.textContent = 'Hakuehdot';
            } else {
                toggleText.textContent = 'Piilota';
            }
            
            setTimeout(updateResetButtonPosition, 350);
        });
        
        updateResetButtonPosition();
    }
}

/**
 * Fade-out efekti oikeassa reunassa
 */
function initScrollFadeIndicator() {
    const tableWrapper = document.querySelector('.table-wrapper');
    const fadeIndicator = document.querySelector('.scroll-fade-indicator');
    
    if (!tableWrapper || !fadeIndicator) return;
    
    function updateFadePosition() {
        const scrollLeft = tableWrapper.scrollLeft;
        const scrollWidth = tableWrapper.scrollWidth;
        const clientWidth = tableWrapper.clientWidth;
        
        const isAtEnd = (scrollLeft + clientWidth >= scrollWidth - 10);
        
        // Tarkista onko kaikki kriitikkosarakkeet näkyvissä
        const table = tableWrapper.querySelector('table');
        let allColumnsVisible = false;
        
        if (table) {
            const thead = table.querySelector('thead');
            if (thead) {
                const allCriticHeaders = thead.querySelectorAll('th.rating-cell');
                const visibleCriticHeaders = Array.from(allCriticHeaders).filter(th => {
                    return th.style.display !== 'none' && !th.classList.contains('filter-hidden');
                });
                
                // Jos kaikki sarakkeet ovat näkyvissä, ei tarvita fadea
                if (visibleCriticHeaders.length === allCriticHeaders.length) {
                    allColumnsVisible = true;
                }
            }
        }
        
        // Piilota fade jos skrollattu loppuun TAI jos kaikki sarakkeet näkyvissä
        if (isAtEnd || allColumnsVisible) {
            fadeIndicator.classList.add('hidden');
        } else {
            fadeIndicator.classList.remove('hidden');
            
            const fadeLeft = scrollLeft + clientWidth - 150;
            fadeIndicator.style.left = fadeLeft + 'px';
        }
        
        const stickyFade = document.querySelector('.scroll-fade-indicator-sticky');
        if (stickyFade) {
            if (isAtEnd || allColumnsVisible) {
                stickyFade.classList.add('hidden');
            } else {
                stickyFade.classList.remove('hidden');
            }
        }
    }
    
    tableWrapper.addEventListener('scroll', updateFadePosition);
    updateFadePosition();
    window.addEventListener('resize', updateFadePosition);
    
    // Exportoi funktio globaalisti
    window.updateScrollFadeIndicator = updateFadePosition;
}

/**
 * Sticky horizontal scrollbar synchronization (desktop only)
 */
function initStickyScrollbar() {
    const isDesktop = () => window.innerWidth >= 769;
    
    if (!isDesktop()) return;
    
    const tableWrapper = document.querySelector('.table-wrapper');
    const stickyScrollbar = document.querySelector('.sticky-scrollbar-container');
    const stickyScrollbarContent = document.querySelector('.sticky-scrollbar-content');
    
    if (!tableWrapper || !stickyScrollbar || !stickyScrollbarContent) return;
    
    let isTableScrolling = false;
    let isStickyScrolling = false;
    
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
    
    tableWrapper.addEventListener('scroll', function() {
        if (isStickyScrolling) return;
        isTableScrolling = true;
        stickyScrollbar.scrollLeft = tableWrapper.scrollLeft;
        setTimeout(() => { isTableScrolling = false; }, 50);
    });
    
    stickyScrollbar.addEventListener('scroll', function() {
        if (isTableScrolling) return;
        isStickyScrolling = true;
        tableWrapper.scrollLeft = stickyScrollbar.scrollLeft;
        setTimeout(() => { isStickyScrolling = false; }, 50);
    });
    
    updateScrollbarWidth();
    window.addEventListener('resize', function() {
        if (isDesktop()) {
            updateScrollbarWidth();
        }
    });
    
    const observer = new MutationObserver(updateScrollbarWidth);
    observer.observe(tableWrapper, { 
        childList: true, 
        subtree: true, 
        attributes: true,
        attributeFilter: ['style', 'class']
    });
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
    initScrollFadeIndicator();
    initStickyScrollbar();
    initColumnCount();
});
