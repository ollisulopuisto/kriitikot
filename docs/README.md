# 📚 Kriitikot - Dokumentaatio

Tämä hakemisto sisältää kaikki projektin dokumentit.

## 📖 Dokumentit

### Käyttöohjeet
- **[PIKAOHJE.md](PIKAOHJE.md)** - Pikaopas projektin käyttöön (aloita tästä!)

### Arkkitehtuuri ja Suunnittelu
- **[REFACTORING.md](REFACTORING.md)** - Scrapers-paketin refaktorointi (1070 riviä → modulaarinen rakenne)
- **[METASCRAPER_DESIGN.md](METASCRAPER_DESIGN.md)** - Automaattisen löytämisen suunnitelma
- **[METASCRAPER_REPORT.md](METASCRAPER_REPORT.md)** - Metascraper-toteutuksen raportti
- **[SUUNNITELMA.md](SUUNNITELMA.md)** - Alkuperäinen projektisuunnitelma

### Ylläpito
- **[ERÄAJO.md](ERÄAJO.md)** - Eräajoskriptien dokumentaatio
- **[CHANGELOG.md](CHANGELOG.md)** - Muutosloki

## 🗂️ Datamalli

Tietokanta `reviews.db` (SQLite) sisältää seuraavat taulut:

### Movies
```sql
CREATE TABLE movies (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE NOT NULL,           -- Normalisoitu elokuvan nimi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Critics
```sql
CREATE TABLE critics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,            -- Kriitikon nimi
    media TEXT,                           -- Pääasiallinen media (esim. "HS")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Publications
```sql
CREATE TABLE publications (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,            -- Julkaisun nimi (esim. "Helsingin Sanomat")
    short_name TEXT UNIQUE NOT NULL,      -- Lyhenne (esim. "hs")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Tuetut julkaisut:**
- `hs` - Helsingin Sanomat
- `ksml` - Keskisuomalainen
- `il` - Iltalehti
- `ts` - Turun Sanomat
- `sk` - Suomen Kuvalehti
- `is` - Ilta-Sanomat

### Reviews
```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL,            -- Viittaus movies-tauluun
    critic_id INTEGER NOT NULL,           -- Viittaus critics-tauluun
    publication_id INTEGER NOT NULL,      -- Viittaus publications-tauluun
    rating_stars INTEGER,                 -- Arvosana 1-5 tähteä (voi olla NULL)
    review_text TEXT,                     -- Arvosteluteksti
    source_url TEXT UNIQUE NOT NULL,      -- Alkuperäinen URL (unique = ei duplikaatteja)
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (critic_id) REFERENCES critics(id),
    FOREIGN KEY (publication_id) REFERENCES publications(id)
);
```

## 🏗️ Projektirakenne

```
kriitikot/
├── docs/                    # 📚 Dokumentaatio
├── src/                     # 💻 Lähdekoodi
│   ├── scrapers/           # 🕷️ Scraper-moduulit (refaktoroitu)
│   │   ├── base.py         # Review & BaseScraper
│   │   ├── hs.py           # Helsingin Sanomat
│   │   ├── ksml.py         # Keskisuomalainen
│   │   ├── il.py           # Iltalehti
│   │   ├── ts.py           # Turun Sanomat
│   │   ├── sk.py           # Suomen Kuvalehti
│   │   └── is_scraper.py   # Ilta-Sanomat
│   ├── app.py              # Flask web-sovellus
│   ├── models.py           # SQLAlchemy-mallit
│   ├── discovery.py        # Automaattinen arvostelujen löytäminen
│   ├── discovery_importer.py  # Tuonti-skripti
│   ├── movie_normalizer.py # Elokuvan nimien normalisointi
│   ├── batch_update.py     # Eräajoskripti
│   └── init_db.py          # Tietokannan alustus
├── tests/                   # 🧪 Testit
│   ├── test_scraper.py     # Scraper-testit (osa backend-testipakettia)
│   └── test_data/          # Testimateriaali
├── templates/               # 🎨 HTML-templatet
├── static/                  # 🎨 CSS/JS
└── reviews.db              # 🗄️ SQLite-tietokanta
```

## � Pääkomennot

```bash
# Web-käyttöliittymä
python3 src/app.py

# Tuo arvosteluja (IS.fi mukana!)
python3 src/discovery_importer.py --source is --limit 10

# Eräajo (päivitä kaikki lähteet)
python3 src/batch_update.py

# Tietokannan tila
python3 src/db_status.py

# Backend-testit
python3 -m pytest -q

# Frontend-testit
npm test
```

## 🔍 Scrapers-paketin rakenne

Jokainen scraper perii `BaseScraper`-luokan ja toteuttaa:

```python
class ExampleScraper:
    def __init__(self):
        self.publication_name = "Publication Name"
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """Parsii HTML:n ja palauttaa Review-objektin"""
        pass
    
    def parse_file(self, filepath: str) -> Optional[Review]:
        """Parsii tiedoston"""
        pass
```

### Review-objekti

```python
@dataclass
class Review:
    movie_title: str                    # Elokuvan nimi
    critic_name: str                    # Kriitikon nimi
    rating_stars: Optional[int]         # 1-5 tähteä tai None
    review_text: Optional[str]          # Arvosteluteksti
    source_url: Optional[str]           # Alkuperäinen URL
    source_publication: str             # Julkaisun nimi
    raw_data: Optional[Dict[str, Any]]  # Raakadata (debug)
```

## 📊 Tilastot

- **Tuetut julkaisut:** 6 kpl (HS, KSML, IL, TS, SK, IS)
- **Scraper-moduulit:** 8 tiedostoa (1240 riviä)
- **Testit:** 55 pytest-testiä + 7 Vitest-testiä (kaikki läpi ✅)
- **Tietokannassa:** 20 arvostelua, 12 elokuvaa, 11 kriitikkoa, 5 julkaisua
- **Refaktorointi:** 1070 riviä → 49 riviä wrapper + 8 modulia
- **Dokumentaatio:** 8 dokumenttia docs/-hakemistossa

## 🔗 Linkit

- **Pääprojekti:** [../README.md](../README.md)
- **Testit:** [../tests/](../tests/)
- **Web UI:** http://localhost:5432 (kun app.py käynnissä)
