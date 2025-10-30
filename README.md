# Elokuvakritiikkien Kerääjä 🎬

Web-sovellus joka kerää, analysoi ja esittää elokuva-arvostelut eri lähteistä.

## 📋 Prototyypin Tila

### ✅ Toimii nyt:
- **Modulaarinen scraper-arkkitehtuuri**: Helppo lisätä uusia lähteitä
- **HS.fi-scraper**: Parsii Helsingin Sanomien arvostelut
- **Tähtiarvioiden parsinta**: Poimii 1-5 tähden arvostelut
- **Web-käyttöliittymä**: Flask-pohjainen sivu arvostelujen näyttämiseen
- **JSON API**: REST-rajapinta arvostelujen hakemiseen
- **Testit**: Pytest-testit scraperille

### 🚧 Työn alla / Tulossa:
- Tietokanta (MySQL)
- Ollama-integraatio (AI-pohjainen arvosanojen generointi)
- Lisää lähteitä (IL, YLE, ym.)
- Elokuvanimien normalisointi
- HTML-taulukkogeneraattori

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
python src/app.py
```

Avaa selaimessa: `http://localhost:5000`

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

# Yleinen funktio joka valitsee oikean scraperin
review = scrape_review(html_content, source='hs')
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

### Python API
```python
from scraper import HSScraper, scrape_review

# Suora scraper-käyttö
scraper = HSScraper()
review = scraper.parse_file('review.html')
print(f"{review.movie_title}: {review.rating_stars}★")

# Yleinen funktio
review = scrape_review(html_content, source='hs')
data = review.to_dict()
```

### HTTP API
```bash
# Hae kaikki arvostelut
curl http://localhost:5000/api/reviews

# Hae yksittäinen arvostelu
curl http://localhost:5000/api/reviews/0
```

## 📝 Seuraavat Askeleet

1. **Tietokanta**: Lisää MySQL-integraatio
2. **Uusia lähteitä**: IL, YLE, Episodi
3. **Ollama**: AI-pohjainen arvosanojen generointi
4. **Scheduler**: Automaattinen ajastus
5. **WordPress-integraatio**: HTML-widget

## 🤝 Kehitysperiaatteet

- **Modulaarisuus**: Jokainen lähde omana moduulinaan
- **Testattavuus**: TDD-lähestymistapa
- **Yleiskäyttöisyys**: Ei kovakoodattuja oletuksia
- **Laajennettavuus**: Helppo lisätä uusia ominaisuuksia

## 📄 Lisenssi

MIT
