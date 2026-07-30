# Kriitikon valinta 🎬

Web-sovellus joka kerää, analysoi ja esittää suomalaisten medioiden elokuva-arvostelut yhdessä paikassa.

## 🌐 Live-sivusto

**Sivusto:** https://ollisulopuisto.github.io/kriitikot/

Päivittyy automaattisesti 6 tunnin välein (GitHub Actions: `.github/workflows/scrape_and_deploy.yml`).

## 📋 Tila

- **11 aktiivista lähdettä**: HS, Keskisuomalainen, Iltalehti, Turun Sanomat, Suomen Kuvalehti, Ilta-Sanomat, Episodi, Muropaketti, Film-O-Holic, Kulttuuritoimitus, Demokraatti
  - Kaleva ja Seura on toteutettu mutta deaktivoitu (maksumuuri / parsintaongelmat)
- **~800 arvostelua, ~230 elokuvaa** SQLite-kannassa (`reviews.db`)
- **Discovery-järjestelmä**: löytää uudet arvostelu-URLit automaattisesti joka lähteestä (`src/discovery.py`)
- **Metatiedot**: TMDB-julisteet, IMDB- ja Letterboxd-linkit (`src/metadata_fetcher.py`)
- **Staattinen julkaisu**: `scripts/generate_static.py` renderöi Flask-sovelluksen `docs/`-kansioon GitHub Pagesia varten
- **Testit**: pytest (backend) + Vitest (frontend)

## 🚀 Asennus ja käyttö

Projekti käyttää [uv](https://docs.astral.sh/uv/):ta riippuvuuksien hallintaan (`pyproject.toml` + `uv.lock`).

```bash
# Asenna riippuvuudet
uv sync --all-extras

# Aja backend-testit
uv run pytest

# Aja frontend-testit
npm install
npm test

# Käynnistä web-sovellus (http://localhost:5432)
uv run python src/app.py
```

### Eräajo — tietokannan päivitys

```bash
# Päivitä kaikki lähteet
cd src && python3 batch_update.py

# Vain yksi lähde
python3 batch_update.py --source hs --limit 10

# Täysi päivitys (20 arvostelua per lähde)
python3 batch_update.py --full

# Bash wrapper (backup + lokitus)
./run_batch_update.sh daily
```

Normaalisti tätä ei tarvitse ajaa käsin — GitHub Actions hoitaa päivityksen 6 tunnin välein ja committaa `reviews.db`:n ja `docs/`-kansion.

### Staattisten sivujen generointi

```bash
uv run python scripts/generate_static.py
```

## 📁 Projektin rakenne

```
kriitikot/
├── src/
│   ├── scrapers/           # Yksi moduuli per julkaisu
│   │   ├── base.py         # Review-dataclass + BaseScraper
│   │   └── __init__.py     # Rekisteri + scrape_review()
│   ├── app.py              # Flask-sovellus
│   ├── models.py           # SQLAlchemy-mallit (Movie, Critic, Publication, Review)
│   ├── discovery.py        # MetaScraper — löytää arvostelu-URLit
│   ├── discovery_importer.py  # discover → scrape → save
│   ├── batch_update.py     # Eräajoskripti
│   ├── metadata_fetcher.py # TMDB/IMDB/Letterboxd-rikastus
│   ├── movie_normalizer.py # Fuzzy-nimimatchaus (kynnys 0.9)
│   └── services/
│       └── data_service.py # Kyselyapurit Flask-näkymille
├── templates/              # Jinja2-templatet
├── static/                 # CSS/JS
├── scripts/generate_static.py  # docs/-kansion generointi
├── tests/                  # pytest + Vitest
├── docs/                   # Generoitu sivusto (GitHub Pages) + dokumentaatio
└── reviews.db              # SQLite-tietokanta (gitissä — Actions tarvitsee)
```

## 🔧 Arkkitehtuuri

**Dataflow:** `discovery.py` löytää URLit → `scrapers/` parsii HTML:n → `discovery_importer.py` tallentaa kantaan → `generate_static.py` julkaisee.

**Tietomalli:** `Movie` ←1:N→ `Review` ←N:1→ `Critic`, `Review` ←N:1→ `Publication`. Duplikaatit estetään `source_url`-UNIQUE-rajoitteella; elokuvien nimet yhdistetään fuzzy-matchauksella.

### Scraperin käyttö

```python
from scrapers import scrape_review

review = scrape_review(html_content, source='hs', source_url=url)
print(f"{review.movie_title}: {review.rating_stars}★ ({review.critic_name})")
```

### Uuden lähteen lisääminen

Katso [AGENTS.md](AGENTS.md) — vaiheittainen ohje (scraper-moduuli, rekisteröinti, discovery, importer, testit).

## 📊 API-endpointit (Flask-kehityspalvelin)

- `GET /` — web-käyttöliittymä
- `GET /api/reviews` — kaikki arvostelut (JSON)
- `GET /api/reviews/<id>` — yksittäinen arvostelu
- `GET /health` — terveystarkistus

## 📚 Dokumentaatio

- **[AGENTS.md](AGENTS.md)** — tekninen referenssi + scraper-ohje (ajantasaisin)
- **[docs/PIKAOHJE.md](docs/PIKAOHJE.md)** — pikaopas
- **[docs/ERÄAJO.md](docs/ERÄAJO.md)** — eräajojen dokumentaatio
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — muutosloki

## 📄 Lisenssi

MIT
