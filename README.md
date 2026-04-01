# Kriitikon valinta 🎬

Web-sovellus joka kerää, analysoi ja esittää elokuva-arvostelut eri lähteistä.

## 🌐 Live-sivusto

**Sivusto:** https://ollisulopuisto.github.io/kriitikot/

Päivittyy automaattisesti päivittäin klo 08:00 Suomen aikaa (GitHub Actions).

## 📋 Prototyypin tila

### ✅ Toimii nyt:
- **🔄 Refaktoroitu arkkitehtuuri**: Modulaarinen scrapers-paketti (ks. [docs/REFACTORING.md](docs/REFACTORING.md))
  - 1070 riviä → 49 riviä wrapper + 8 modulia
  - Jokainen scraper omassa tiedostossaan
- **8 toimivaa scraperia**:
  - **HS.fi**: Helsingin Sanomat (Next.js JSON, puhdas title extraction)
  - **KSML.fi**: Keskisuomalainen (aria-label + JSON-LD, maksumuurin takana)
  - **IL.fi**: Iltalehti (⭐-symbolit, regex "IL-arvio: ⭐⭐", double-encoded UTF-8)
  - **TS.fi**: Turun Sanomat (★-symbolit, maksumuurin takana, intro-tag)
  - **SK.fi**: Suomen Kuvalehti (meta og:title, "[Nimi] kirjoittaa" pattern)
  - **IS.fi**: Ilta-Sanomat (Next.js JSON, TV-lehti-tagit)
  - **Episodi.fi**: WordPress JSON API, JSON-LD schema ratings
  - **Muropaketti.com**: Image filename ratings, structured info box
- **🔍 Discovery-system**: Automaattinen arvostelujen löytäminen kaikista lähteistä!
  - HS: Next.js JSON parsing (storyLogo: "Elokuva-arvio")
  - TS: HTML category page (span "Elokuva-arvostelu")
  - IL: JSON API embedded data (fixed regex + UUID validation)
  - KSML: Search page parsing
  - SK: Tag-based category crawling
  - IS: Next.js JSON (TV & Elokuvat tags)
  - Episodi: WordPress JSON REST API (/wp-json/wp/v2/)
  - Muropaketti: Category page with span.category-name
- **📊 Tietokanta**: SQLite + SQLAlchemy ORM
  - Movies, Critics, Publications, Reviews
  - Automaattinen duplikaattien välttäminen (URL-perusteinen)
  - Fuzzy matching elokuvan nimille (0.9 threshold)
  - **66 arvostelua 8 julkaisusta** (Nov 2025)
- **🤖 Eräajo-system**: Automaattinen tietokannan päivitys
  - `batch_update.py`: Python-scripti päivityksiin
  - `run_batch_update.sh`: Bash wrapper backupilla ja logeilla
  - Cron/systemd -valmiit konfiguraatiot
- **🚀 GitHub Pages deployment**: Staattiset sivut automaattisella päivityksellä
  - `scripts/generate_static.py`: Generoi docs/ kansio Flask-appista
  - GitHub Actions: `.github/workflows/update-site.yml` + `deploy-pages.yml`
  - Ei tietoturva-aukkoja (staattiset sivut, ei backend)
- **Tähtiarvioiden parsinta**: 1-5 tähteä + suomenkieliset sanat ("neljä tähteä")
- **Web-käyttöliittymä**: Flask-pohjainen sivu arvostelujen näyttämiseen
  - Kompakti admin-näkymä (80-100px sarakkeet)
  - Ulkoinen CSS-tiedosto (static/style.css)
  - Sarakkeiden järjestyksen muuttaminen
- **JSON API**: REST-rajapinta arvostelujen hakemiseen
- **Testit**: 55 backend-testiä (pytest) + 7 frontend-testiä (Vitest) ✅
- **🤖 AI Agent Instructions**: [AGENTS.md](AGENTS.md) - Ohjeet uusien scrapereiden lisäämiseen

### 🚧 Työn alla / Tulossa:
- **Film-O-Holic scraper**: Työn alla 🚧
- **Web UI -parannukset**: Suodattimet, haku, järjestely
- **Ollama-integraatio**: AI-pohjainen arvosanojen generointi kun tähtiä ei ole
- **Lisää lähteitä**: YLE Areena, Episodi.fi
- **RSS Feed Crawler**: Vaihtoehtoinen discovery-metodi

## 📚 Dokumentaatio

Kaikki dokumentaatio löytyy [docs/](docs/) -hakemistosta:

- **[AGENTS.md](AGENTS.md)** - AI-ohje scrapereiden lisäämiseen (uusi!) 🤖
- **[docs/PIKAOHJE.md](docs/PIKAOHJE.md)** - Pikaopas käyttöön (aloita tästä!)
- **[docs/REFACTORING.md](docs/REFACTORING.md)** - Scrapers-paketin refaktorointi
- **[docs/METASCRAPER_DESIGN.md](docs/METASCRAPER_DESIGN.md)** - Discovery-systeemin suunnitelma
- **[docs/METASCRAPER_REPORT.md](docs/METASCRAPER_REPORT.md)** - Discovery-toteutus
- **[docs/ERÄAJO.md](docs/ERÄAJO.md)** - Eräajoskriptien dokumentaatio
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Muutosloki
- **[docs/README.md](docs/README.md)** - Datamalli ja arkkitehtuuri

## 🚀 Asennus ja Käyttö

### 1. Asenna riippuvuudet
```bash
pip install -r requirements.txt
```

### 2. Aja testit
```bash
pytest tests/test_scraper.py -v
```

### 3. Käynnistä web-sovellus
```bash
python3 src/app.py
```

#### Paikallinen kehitys (kontti samalla koneella)
Avaa selaimessa: `http://localhost:5432`

#### Remote-kehitys (VS Code Dev Container)

**Vaihtoehto A: VS Code Simple Browser (suositeltu)**
1. Paina `Ctrl+Shift+P` (tai `Cmd+Shift+P` macOS)
2. Kirjoita: "Simple Browser: Show"
3. Anna URL: `http://localhost:5432`

**Vaihtoehto B: SSH-tunneli läppärille**

Jos Flask pyörii remote-koneella (esim. `dev.sulopuis.to`), luo SSH-tunneli **läppärilläsi**:

```bash
# Jos VS Code jo forwardaa portin 5432, käytä eri porttia:
ssh -L 8000:localhost:5432 käyttäjä@dev.sulopuis.to

# Tai jos portti 5432 on vapaa:
ssh -L 5432:localhost:5432 käyttäjä@dev.sulopuis.to
```

Sitten avaa läppärin selaimessa:
- `http://localhost:8000` (jos käytit porttia 8000)
- `http://localhost:5432` (jos käytit porttia 5432)

**Huom:** `forwardPorts` devcontainer.json:ssa ei riitä remote-käytössä - tarvitaan SSH-tunneli tai Simple Browser.

**Vaihtoehto C: Automaattinen tunneli (autossh)**

Voit automatisoida tunnelin autossh-työkalulla:
```bash
# Asenna autossh (läppärillä)
# macOS: brew install autossh
# Linux: sudo apt-get install autossh

# Luo pysyvä tunneli
autossh -M 0 -f -N -L 8000:localhost:5432 käyttäjä@dev.sulopuis.to
```

Tunneli pysyy pystyssä ja yhdistää automaattisesti uudelleen jos yhteys katkeaa.

### 4. Generoi staattiset sivut (GitHub Pages)

```bash
# Generoi docs/ kansio
python scripts/generate_static.py

# Push GitHubiin
git add docs/ reviews.db
git commit -m "Päivitä staattiset sivut"
git push
```

**GitHub Pages asetukset:**
1. GitHub → Settings → Pages
2. Source: `main` branch
3. Folder: `/docs`

**Automaattinen päivitys:** GitHub Actions hoitaa päivittäisen päivityksen (ks. `.github/workflows/`)

### 5. Eräajo - Tietokannan automaattinen päivitys

#### Manuaalinen käyttö

```bash
# Päivitä kaikki lähteet (5 arvostelua per lähde)
cd src && python3 batch_update.py

# Päivitä vain HS.fi, 10 arvostelua
python3 batch_update.py --source hs --limit 10

# Täysi päivitys (20 arvostelua per lähde)
python3 batch_update.py --full

# Bash wrapper (sisältää backupin ja lokituksen)
./run_batch_update.sh daily
./run_batch_update.sh weekly
./run_batch_update.sh hourly
```

#### Automaattinen ajastus (Cron)

```bash
# Muokkaa crontab:
crontab -e

# Päivittäinen päivitys klo 08:00
0 8 * * * /workspaces/kriitikot/src/run_batch_update.sh daily

# Päivitys 3 kertaa päivässä
0 8,14,20 * * * /workspaces/kriitikot/src/run_batch_update.sh hourly

# Täysi päivitys viikonloppuisin
0 10 * * 0,6 /workspaces/kriitikot/src/run_batch_update.sh weekly
```

📖 **Tarkemmat ohjeet**: Katso [docs/ERÄAJO.md](docs/ERÄAJO.md) systemd-timer ja muut vaihtoehdot.


## 📁 Projektin Rakenne

```
kriitikot/
├── docs/                    # 📚 Dokumentaatio
│   ├── README.md           # Datamalli ja arkkitehtuuri
│   ├── PIKAOHJE.md         # Käyttöohje
│   ├── REFACTORING.md      # Refaktorointi-raportti
│   ├── METASCRAPER_*.md    # Discovery-dokumentaatio
│   ├── ERÄAJO.md           # Eräajo-ohje
│   └── CHANGELOG.md        # Muutosloki
├── src/
│   ├── scrapers/           # 🕷️ Modulaariset scraperit
│   │   ├── base.py         # Review + BaseScraper
│   │   ├── hs.py           # Helsingin Sanomat
│   │   ├── ksml.py         # Keskisuomalainen
│   │   ├── il.py           # Iltalehti
│   │   ├── ts.py           # Turun Sanomat
│   │   ├── sk.py           # Suomen Kuvalehti
│   │   ├── is_scraper.py   # Ilta-Sanomat
│   │   ├── episodi.py      # Episodi.fi
│   │   └── muropaketti.py  # Muropaketti.com
│   ├── scraper.py          # Backward compatibility wrapper
│   ├── app.py              # Flask web-sovellus
│   ├── models.py           # SQLAlchemy-mallit
│   ├── discovery.py        # Automaattinen löytäminen
│   ├── discovery_importer.py  # Tuonti-skripti
│   ├── movie_normalizer.py # Elokuvan nimien normalisointi
│   ├── batch_update.py     # Eräajoskripti
│   └── init_db.py          # Tietokannan alustus
├── templates/              # 🎨 HTML-templatet
├── static/                 # 🎨 CSS/JS
├── tests/                  # 🧪 Testit
│   ├── test_scraper.py    # Scraper-testit (13 testiä)
│   └── test_data/         # Testimateriaali
├── reviews.db             # 🗄️ SQLite-tietokanta
├── requirements.txt
└── pyproject.toml
```

## 🔧 Arkkitehtuuri

### Review-luokka
Yhtenäinen tietorakenne kaikille arvosteluille:
```python
Review(
    movie_title="Elokuvan nimi",
    critic_name="Kriitikon nimi",
    rating_stars=4,  # 1-5 tai None
    review_text="Arvostelun teksti...",
    source_url="https://...",
    source_publication="Helsingin Sanomat"
)
```

### Scrapers
Jokainen lähde omassa moduulissaan `scrapers/`-paketissa:
```python
# Käytä suoraan
from scrapers import HSScraper
scraper = HSScraper()
review = scraper.parse_html(html_content)

# Tai yleistä funktiota
from scrapers import scrape_review
review = scrape_review(html_content, source='hs')  # hs, ksml, il, ts, sk, is, episodi, muropaketti
```

Ks. [docs/REFACTORING.md](docs/REFACTORING.md) lisätietoja modulaarisesta rakenteesta.

### Uuden lähteen lisääminen
1. Luo uusi scraper-moduuli `src/scrapers/example.py`
2. Toteuta `parse_html()`-metodi
3. Palauta `Review`-objekti
4. Lisää `scrapers/__init__.py`-tiedoston `scrapers`-dictionaryyn

Ks. [docs/README.md](docs/README.md) yksityiskohtaiset ohjeet.

## 🧪 Testaus

```bash
# Backend-testit (pytest)
python3 -m pytest -q

# Frontend-testit (Vitest)
npm test

# Yksittäinen testi
pytest tests/test_scraper.py::test_hs_scraper_basic -v

# Verbose-tilassa
pytest -v -s
```

## 📊 API Endpoints

- `GET /` - Web-käyttöliittymä
- `GET /api/reviews` - JSON: kaikki arvostelut
- `GET /api/reviews/<id>` - JSON: yksittäinen arvostelu
- `GET /health` - Terveystarkistus

## 💡 Esimerkkejä

### Python API - Scraping
```python
from scrapers import HSScraper, scrape_review

# Suora scraper-käyttö
scraper = HSScraper()
review = scraper.parse_file('review.html')
print(f"{review.movie_title}: {review.rating_stars}★")

# Yleinen funktio (suositeltu)
review = scrape_review(html_content, source='hs')  # hs, ksml, il, ts, sk, is, episodi, muropaketti
data = review.to_dict()
```

### Python API - Discovery (Metascraper)
```python
from discovery import MetaScraper

# Luo metascraper
meta = MetaScraper()

# Hae 10 uusinta arvostelua Suomen Kuvalehdestä
reviews = meta.discover_new_reviews('sk', limit=10)

for rev in reviews:
    print(f"{rev['title']}")
    print(f"  URL: {rev['url']}")

# Esikatsele löydökset
meta.preview_discoveries('sk', count=5)
```

### Yhdistä Discovery + Scraping
```python
from discovery import MetaScraper
from scrapers import scrape_review
import requests

meta = MetaScraper()
reviews = meta.discover_new_reviews('sk', limit=3)

for rev_meta in reviews:
    url = rev_meta['url']
    
    # Hae HTML
    html = requests.get(url).text
    
    # Parsii
    review = scrape_review(html, source='sk', source_url=url)
    
    if review:
        print(f"✅ {review.movie_title} - {review.rating_stars}/5★")
        print(f"   by {review.critic_name}")
```

### HTTP API
```bash
# Hae kaikki arvostelut
curl http://localhost:5432/api/reviews

# Hae yksittäinen arvostelu
curl http://localhost:5432/api/reviews/0
```

## 📝 Seuraavat Askeleet

1. **Web UI -parannukset**: Suodattimet, haku, järjestely
2. **Ollama AI**: Generoi puuttuvia arvosanoja
3. **APScheduler**: Ajasta discovery automaattisesti (joka 6h)
4. **Lisää lähteitä**: YLE Areena, Episodi.fi
5. **RSS Feed Crawler**: Vaihtoehtoinen discovery-metodi

📖 **Lisää dokumentaatiota:** [docs/](docs/) -hakemisto

## 🤝 Kehitysperiaatteet

- **Modulaarisuus**: Jokainen lähde omana moduulinaan
- **Testattavuus**: Hyvä regressiotestikattavuus (backend + frontend), mutta ei järjestelmällistä red-green TDD -prosessia kaikissa muutoksissa
- **Yleiskäyttöisyys**: Ei kovakoodattuja oletuksia
- **Laajennettavuus**: Helppo lisätä uusia ominaisuuksia

## 📄 Lisenssi

MIT
