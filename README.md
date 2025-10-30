# Elokuvakritiikkien Kerääjä 🎬

Web-sovellus joka kerää, analysoi ja esittää elokuva-arvostelut eri lähteistä.

## 📋 Prototyypin Tila

### ✅ Toimii nyt:
- **Modulaarinen scraper-arkkitehtuuri**: Helppo lisätä uusia lähteitä
- **5 toimivaa scraperia**:
  - **HS.fi**: Helsingin Sanomat (Next.js JSON, puhdas title extraction)
  - **KSML.fi**: Keskisuomalainen (aria-label + JSON-LD, maksumuurin takana)
  - **IL.fi**: Iltalehti (⭐-symbolit, regex "IL-arvio: ⭐⭐")
  - **TS.fi**: Turun Sanomat (★-symbolit, maksumuurin takana, intro-tag)
  - **SK.fi**: Suomen Kuvalehti (meta og:title, "[Nimi] kirjoittaa" pattern)
- **🔍 Discovery-system**: Automaattinen arvostelujen löytäminen kaikista lähteistä!
  - HS: Next.js JSON parsing (storyLogo: "Elokuva-arvio")
  - TS: HTML category page (span "Elokuva-arvostelu")
  - IL: JSON API embedded data
  - KSML: Search page parsing
  - SK: Tag-based category crawling
- **📊 Tietokanta**: SQLite + SQLAlchemy ORM
  - Movies, Critics, Publications, Reviews
  - Automaattinen duplikaattien välttäminen (URL-perusteinen)
  - 16 arvostelua tietokannassa (HS, TS, IL, KSML, SK)
- **🤖 Eräajo-system**: Automaattinen tietokannan päivitys
  - `batch_update.py`: Python-scripti päivityksiin
  - `run_batch_update.sh`: Bash wrapper backupilla ja logeilla
  - Cron/systemd -valmiit konfiguraatiot
- **Tähtiarvioiden parsinta**: 1-5 tähteä + suomenkieliset sanat ("neljä tähteä")
- **Web-käyttöliittymä**: Flask-pohjainen sivu arvostelujen näyttämiseen
- **JSON API**: REST-rajapinta arvostelujen hakemiseen
- **Testit**: 12 pytest-testiä (100% passing - HS, KSML, IL, TS, SK)

### 🚧 Työn alla / Tulossa:
- **Web UI -parannukset**: Parempi käyttöliittymä tietokannalle
- **Elokuvanimien normalisointi**: Samaan elokuvaan liittyvät arvostelut yhteen
- **Ollama-integraatio**: AI-pohjainen arvosanojen generointi kun tähtiä ei ole
- **Lisää lähteitä**: YLE Areena, Episodi.fi
- **RSS Feed Crawler**: Vaihtoehtoinen discovery-metodi
- **HTML-taulukkogeneraattori**: WordPress-widget

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
Avaa selaimessa: `http://localhost:5000`

#### Remote-kehitys (VS Code Dev Container)

**Vaihtoehto A: VS Code Simple Browser (suositeltu)**
1. Paina `Ctrl+Shift+P` (tai `Cmd+Shift+P` macOS)
2. Kirjoita: "Simple Browser: Show"
3. Anna URL: `http://localhost:5000`

**Vaihtoehto B: SSH-tunneli läppärille**

Jos Flask pyörii remote-koneella (esim. `dev.sulopuis.to`), luo SSH-tunneli **läppärilläsi**:

```bash
# Jos VS Code jo forwardaa portin 5000, käytä eri porttia:
ssh -L 8000:localhost:5000 käyttäjä@dev.sulopuis.to

# Tai jos portti 5000 on vapaa:
ssh -L 5000:localhost:5000 käyttäjä@dev.sulopuis.to
```

Sitten avaa läppärin selaimessa:
- `http://localhost:8000` (jos käytit porttia 8000)
- `http://localhost:5000` (jos käytit porttia 5000)

**Huom:** `forwardPorts` devcontainer.json:ssa ei riitä remote-käytössä - tarvitaan SSH-tunneli tai Simple Browser.

**Vaihtoehto C: Automaattinen tunneli (autossh)**

Voit automatisoida tunnelin autossh-työkalulla:
```bash
# Asenna autossh (läppärillä)
# macOS: brew install autossh
# Linux: sudo apt-get install autossh

# Luo pysyvä tunneli
autossh -M 0 -f -N -L 8000:localhost:5000 käyttäjä@dev.sulopuis.to
```

Tunneli pysyy pystyssä ja yhdistää automaattisesti uudelleen jos yhteys katkeaa.

### 4. Eräajo - Tietokannan automaattinen päivitys

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

📖 **Tarkemmat ohjeet**: Katso [ERÄAJO.md](ERÄAJO.md) systemd-timer ja muut vaihtoehdot.


## 📁 Projektin Rakenne

```
kriitikot/
├── src/
│   ├── scraper.py      # Modulaarinen scraper (HS + tulevat lähteet)
│   └── app.py          # Flask web-sovellus
├── templates/
│   └── index.html      # HTML-template arvosteluille
├── tests/
│   ├── test_scraper.py # Scraper-testit
│   └── test_data/      # Test HTML-tiedostot
├── requirements.txt
└── SUUNNITELMA.md
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
Jokaisella lähteellä oma scraper-luokka:
```python
# Helsingin Sanomat
scraper = HSScraper()
review = scraper.parse_html(html_content)

# Keskisuomalainen
scraper = KSMLScraper()
review = scraper.parse_html(html_content)

# Yleinen funktio joka valitsee oikean scraperin
review = scrape_review(html_content, source='hs')  # tai source='ksml'
```

### Uuden lähteen lisääminen
1. Luo uusi scraper-luokka (esim. `ILScraper`)
2. Toteuta `parse_html()`-metodi
3. Palauta `Review`-objekti
4. Lisää `scrape_review()`-funktion `scrapers`-sanakirjaan

## 🧪 Testaus

```bash
# Kaikki testit
pytest

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
from scraper import HSScraper, scrape_review

# Suora scraper-käyttö
scraper = HSScraper()
review = scraper.parse_file('review.html')
print(f"{review.movie_title}: {review.rating_stars}★")

# Yleinen funktio
review = scrape_review(html_content, source='hs')  # tai 'ksml', 'il', 'ts', 'sk'
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
from scraper import scrape_review
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
curl http://localhost:5000/api/reviews

# Hae yksittäinen arvostelu
curl http://localhost:5000/api/reviews/0
```

## 📝 Seuraavat Askeleet

1. **Metascraperin laajentaminen**: Lisää kategoriasivut muille lähteille (HS, KSML, IL, TS)
2. **MySQL-tietokanta**: Tallenna arvostelut pysyvästi
3. **Deduplication**: Älä scrapaa samaa arvostelua kahdesti
4. **APScheduler**: Ajasta discovery automaattisesti (joka 6h)
5. **RSS Feed Crawler**: Vaihtoehtoinen discovery-metodi
6. **Ollama AI**: Generoi puuttuvia arvosanoja
7. **WordPress-integraatio**: HTML-widget

📖 **Lisää dokumentaatiota:**
- `METASCRAPER_DESIGN.md` - Metascraperin arkkitehtuurisuunnittelu (4 eri lähestymistapaa)
- `METASCRAPER_REPORT.md` - Toteutusraportti ja käyttöohjeet
- `CHANGELOG.md` - Versiohistoria ja muutokset

## 🤝 Kehitysperiaatteet

- **Modulaarisuus**: Jokainen lähde omana moduulinaan
- **Testattavuus**: TDD-lähestymistapa
- **Yleiskäyttöisyys**: Ei kovakoodattuja oletuksia
- **Laajennettavuus**: Helppo lisätä uusia ominaisuuksia

## 📄 Lisenssi

MIT
