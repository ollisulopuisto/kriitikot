# Scrapers Package Refactoring

## 📊 Refaktoroinnin tulokset

### Ennen refaktorointia:
- **1 tiedosto**: `scraper.py` (1,070 riviä)
- Kaikki 6 scraperia samassa tiedostossa
- Vaikea navigoida ja ylläpitää

### Refaktoroinnin jälkeen:
- **8 modulaarista tiedostoa** scrapers-paketissa
- **49 riviä** backward compatibility wrapper (`scraper.py`)
- Selkeä rakenne, helppo laajentaa

## 📁 Uusi tiedostorakenne

```
src/
├── scraper.py              (49 riviä - backward compatibility wrapper)
├── scraper.py.backup       (1,069 riviä - varmuuskopio)
└── scrapers/               (uusi paketti)
    ├── __init__.py         (84 riviä - registry ja exports)
    ├── base.py             (78 riviä - Review + BaseScraper)
    ├── hs.py               (152 riviä - Helsingin Sanomat)
    ├── ksml.py             (283 riviä - Keskisuomalainen)
    ├── il.py               (117 riviä - Iltalehti)
    ├── ts.py               (157 riviä - Turun Sanomat)
    ├── sk.py               (141 riviä - Suomen Kuvalehti)
    └── is_scraper.py       (228 riviä - Ilta-Sanomat)
```

## 🔄 Käyttö

### Uusi tapa (suositeltu):
```python
from scrapers import HSScraper, Review, scrape_review

# Käytä suoraan scraperia
scraper = HSScraper()
review = scraper.parse_file('test.html')

# Tai yleistä funktiota
review = scrape_review(html_content, source='hs')
```

### Vanha tapa (toimii edelleen):
```python
from scraper import HSScraper, Review, scrape_review
# ^ Tämä antaa DeprecationWarning mutta toimii
```

## ✅ Testit

Kaikki 13 testiä menevät läpi:
- ✅ test_hs_scraper_basic
- ✅ test_scrape_review_general_function
- ✅ test_review_to_dict
- ✅ test_unknown_source
- ✅ test_ksml_scraper_basic
- ✅ test_ksml_via_general_function
- ✅ test_il_scraper_basic
- ✅ test_il_via_general_function
- ✅ test_ts_scraper_basic
- ✅ test_ts_via_general_function
- ✅ test_sk_scraper_basic
- ✅ test_sk_via_general_function
- ✅ test_is_scraper

## 🎯 Edut

1. **Modulaarisuus**: Jokainen scraper omassa tiedostossaan
2. **Ylläpidettävyys**: Helpompi löytää ja korjata bugit
3. **Testattavuus**: Voi testata yksittäisiä scrapereita
4. **Laajennettavuus**: Uuden scraperin lisääminen on helppoa
5. **Backward compatibility**: Vanhat importit toimivat edelleen
6. **Pienempi kognitiivinen kuorma**: ~150-280 riviä per tiedosto vs. 1070

## 🚀 Uuden scraperin lisääminen

1. Luo uusi tiedosto `src/scrapers/example.py`:
```python
from .base import Review
from bs4 import BeautifulSoup

class ExampleScraper:
    def __init__(self):
        self.publication_name = "Example Publication"
    
    def parse_html(self, html_content, source_url=None):
        # Parsimislogiikka tähän
        return Review(...)
    
    def parse_file(self, filepath):
        with open(filepath, 'r') as f:
            return self.parse_html(f.read())
```

2. Lisää `src/scrapers/__init__.py`:
```python
from .example import ExampleScraper

scrapers = {
    # ...
    'example': ExampleScraper(),
}
```

3. Valmis! Käyttö: `scrape_review(html, source='example')`

## 📝 Muutoshistoria

**2025-10-30**: Refaktoroitu scraper.py modulaariseksi scrapers-paketiksi
- Luotu 8 uutta tiedostoa
- Säilytetty täysi backward compatibility
- Kaikki testit menevät läpi
