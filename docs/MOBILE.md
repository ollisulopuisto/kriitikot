# Mobiililayoutin hakufasetit - Tekninen dokumentaatio

## Yleiskuvaus

Mobiililayoutissa desktop-sliderit on korvattu stepper-painikkeilla ([-] arvo [+]) parempaa käytettävyyttä varten. Kosketusnäytöllä slidereiden vetäminen on hankalaa, joten painikkeet ovat 44×44px kosketuskohteet.

## HTML-rakenne

Mobiilisuodattimet sijaitsevat `templates/index.html` tiedostossa, noin rivit 200-240:

```html
<div class="mobile-filter">
    <div class="mobile-filters-container">
        <!-- Fasetti 1: Arvioiden määrä -->
        <div class="mobile-filter-group mobile-filter-inline">
            <label>Arvosteluja:</label>
            <div class="mobile-stepper">
                <button class="stepper-btn" id="reviews-minus-mobile" aria-label="Vähemmän">−</button>
                <span class="stepper-value" id="min-reviews-value-mobile">1</span>
                <button class="stepper-btn" id="reviews-plus-mobile" aria-label="Enemmän">+</button>
            </div>
        </div>
        
        <!-- Fasetti 2: Tähdet -->
        <div class="mobile-filter-group mobile-filter-inline">
            <label>Arvosana:</label>
            <div class="mobile-stepper">
                <button class="stepper-btn" id="stars-minus-mobile" aria-label="Pienempi">−</button>
                <span class="stepper-value" id="star-filter-value-mobile">Kaikki</span>
                <button class="stepper-btn" id="stars-plus-mobile" aria-label="Suurempi">+</button>
            </div>
        </div>
        
        <!-- Fasetti 3: Media -->
        <div class="mobile-filter-group">
            <label>Julkaisu:</label>
            <div class="media-filter-buttons">
                {% for pub, count in pub_stats.items() %}
                <button class="media-filter-btn filter-publication" data-publication="{{ pub }}" title="Näytä {{ pub }}-arvostelut">
                    {{ pub }}
                </button>
                {% endfor %}
            </div>
        </div>
        
        <!-- Fasetti 4: Aakkostus -->
        <div class="mobile-filter-group">
            <div class="mobile-sort-button" id="mobile-sort" style="cursor: pointer; text-align: center; padding: 0.75rem; background: #f0f0f0; border-radius: 0.5rem; font-weight: bold; border: 1px solid #ddd;">
                ▼ Aakkosta elokuvat
            </div>
        </div>
    </div>
</div>
```

## JavaScript-logiikka

### Arvioiden määrä -stepper (rivit ~520-570)

```javascript
// Mobile stepper buttons (korvaa sliderin)
const reviewsMinusBtn = document.getElementById('reviews-minus-mobile');
const reviewsPlusBtn = document.getElementById('reviews-plus-mobile');

if (reviewsMinusBtn && reviewsPlusBtn && valueDisplayMobile) {
    let currentValue = 1;
    
    const updateReviewStepper = (newValue) => {
        currentValue = Math.max(1, Math.min(5, newValue));
        valueDisplayMobile.textContent = currentValue;
        valueDisplay.textContent = currentValue;
        slider.value = currentValue;
        updateReviewWord(currentValue);
        filterByReviewCount(currentValue);
        
        // Disable buttons at limits
        reviewsMinusBtn.disabled = currentValue <= 1;
        reviewsPlusBtn.disabled = currentValue >= 5;
    };
    
    reviewsMinusBtn.addEventListener('click', () => updateReviewStepper(currentValue - 1));
    reviewsPlusBtn.addEventListener('click', () => updateReviewStepper(currentValue + 1));
    
    // Initialize button states
    updateReviewStepper(1);
}
```

**Tärkeää:**
- `currentValue` on closure-muuttuja joka säilyttää tilan
- Synkronoi desktop-sliderin kanssa (`slider.value = currentValue`)
- Painikkeet disabloituvat rajoissa (1-5)
- Kutsuu `filterByReviewCount(currentValue)` ja `updateCriticColumnVisibility()`

### Tähtisuodatin-stepper (rivit ~690-725)

```javascript
// Mobile stepper buttons (korvaa sliderin)
const starsMinusBtn = document.getElementById('stars-minus-mobile');
const starsPlusBtn = document.getElementById('stars-plus-mobile');

if (starsMinusBtn && starsPlusBtn) {
    let currentValue = 0;
    
    const updateStarStepper = (newValue) => {
        currentValue = Math.max(0, Math.min(5, newValue));
        
        updateStarLabel(currentValue);
        starSlider.value = currentValue;
        filterByStars(currentValue);
        
        // Update button states
        starsMinusBtn.disabled = (currentValue <= 0);
        starsPlusBtn.disabled = (currentValue >= 5);
    };
    
    starsMinusBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (!this.disabled) {
            updateStarStepper(currentValue - 1);
        }
    });
    
    starsPlusBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (!this.disabled) {
            updateStarStepper(currentValue + 1);
        }
    });
    
    // Initialize button states
    updateStarStepper(0);
}
```

**Tärkeää:**
- Arvoalue 0-5 (0 = "Kaikki")
- `preventDefault()` ja `stopPropagation()` estävät oletustoiminnon
- Synkronoi desktop-sliderin kanssa
- Kutsuu `filterByStars(currentValue)` ja `updateCriticColumnVisibility()`

### Reset-nappi (rivit ~760-800)

```javascript
resetButton.addEventListener('click', function() {
    // Nollaa suodattimet
    const slider = document.getElementById('min-reviews-slider');
    const starSlider = document.getElementById('star-filter-slider');
    
    if (slider) slider.value = 1;
    if (starSlider) starSlider.value = 0;
    
    const valueDisplay = document.getElementById('min-reviews-value');
    const valueDisplayMobile = document.getElementById('min-reviews-value-mobile');
    const starValueDisplay = document.getElementById('star-filter-value');
    const starValueDisplayMobile = document.getElementById('star-filter-value-mobile');
    
    if (valueDisplay) valueDisplay.textContent = '1';
    if (valueDisplayMobile) valueDisplayMobile.textContent = '1';
    if (starValueDisplay) starValueDisplay.innerHTML = 'Kaikki';
    if (starValueDisplayMobile) starValueDisplayMobile.innerHTML = 'Kaikki';
    
    // Reset mobile stepper buttons
    const reviewsMinusBtn = document.getElementById('reviews-minus-mobile');
    const reviewsPlusBtn = document.getElementById('reviews-plus-mobile');
    const starsMinusBtn = document.getElementById('stars-minus-mobile');
    const starsPlusBtn = document.getElementById('stars-plus-mobile');
    
    if (reviewsMinusBtn) reviewsMinusBtn.disabled = true;
    if (reviewsPlusBtn) reviewsPlusBtn.disabled = false;
    if (starsMinusBtn) starsMinusBtn.disabled = true;
    if (starsPlusBtn) starsPlusBtn.disabled = false;
    
    // ... muut reset-toiminnot ...
});
```

## CSS-tyylit (static/style.css, rivit ~880-950)

```css
.mobile-filter-group.mobile-filter-inline {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

.mobile-filter-group.mobile-filter-inline label {
    flex-shrink: 0;
    white-space: nowrap;
    font-size: 0.9em;
}

.mobile-stepper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    justify-content: flex-end;
}

.stepper-btn {
    width: 44px;
    height: 44px;
    border: 2px solid #8b5cf6;
    background: white;
    border-radius: 8px;
    font-size: 1.5em;
    font-weight: bold;
    color: #8b5cf6;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
}

.stepper-btn:active {
    background: #8b5cf6;
    color: white;
    transform: scale(0.95);
}

.stepper-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.stepper-value {
    min-width: 60px;
    text-align: center;
    font-weight: 600;
    font-size: 1em;
    color: #333;
}
```

**Tärkeimmät ominaisuudet:**
- 44×44px kosketuskohteet (Apple HIG suositus)
- Violetti värimaailma (#8b5cf6) yhtenäisyyden vuoksi
- `:active` -pseudo antaa visuaalisen palautteen
- `:disabled` -tila himmennetty (opacity 0.3)
- `user-select: none` estää tekstin vahingossa valitsemisen
- `-webkit-tap-highlight-color: transparent` estää sinisen korostuksen iOS:ssä

## Arkkitehtuuri

```
Desktop Slider ←→ Mobile Stepper
       ↓              ↓
   Keskitetty filtteröintilogiikka
   (filterByReviewCount / filterByStars)
       ↓
   updateCriticColumnVisibility()
```

**Synkronointi:** Desktop-slider ja mobile-stepper päivittävät toistensa arvoja jotta tila pysyy konsistenttina näkymien välillä.

**Suodatinlogiikka:**
1. Desktop: Piilottaa taulukon rivejä (`<tr>` display:none)
2. Mobile: Piilottaa kortteja (`.movie-card` display:none)
3. Molemmat: Kutsuu `updateCriticColumnVisibility()` joka piilottaa tyhjiä kriitikkosarakkeita

## Palauttaminen käyttöön

Jos HTML/JS on menetetty, kopioi:

1. **HTML:** Rivit 200-240 (`<div class="mobile-filter">...</div>`)
2. **JavaScript - Arvioiden määrä:** Rivit ~520-570 (stepper-painikkeet + event handlerit)
3. **JavaScript - Tähdet:** Rivit ~690-725 (stepper-painikkeet + event handlerit)
4. **JavaScript - Reset:** Rivit ~760-800 (mobile stepper reset-logiikka)
5. **CSS:** Rivit ~880-950 (`.mobile-stepper`, `.stepper-btn`, `.stepper-value`)

## Testaus

Testaa että:
- [ ] Painikkeet toimivat (arvot muuttuvat)
- [ ] Painikkeet disabloituvat rajoissa (1/0 ja 5)
- [ ] Desktop-slider synkronoituu mobiilin kanssa
- [ ] Suodatus toimii (kortit piiloutuvat/näkyvät)
- [ ] Reset-nappi nollaa stepper-painikkeet
- [ ] Visuaalinen palaute (`:active` tila) toimii
- [ ] 44×44px kosketuskohteet ovat riittävän suuret

## Kriittiset ID:t

- `reviews-minus-mobile` - Arvioiden määrä miinus-painike
- `reviews-plus-mobile` - Arvioiden määrä plus-painike
- `min-reviews-value-mobile` - Arvioiden määrä arvo (span)
- `stars-minus-mobile` - Tähdet miinus-painike
- `stars-plus-mobile` - Tähdet plus-painike
- `star-filter-value-mobile` - Tähdet arvo (span, sisältö voi olla "Kaikki" tai "★★★")

Älä poista tai nimeä näitä uudelleen ilman JavaScript-koodin päivittämistä!
