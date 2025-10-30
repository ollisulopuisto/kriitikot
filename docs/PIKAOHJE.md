# Kriitikot - Pikaohje 🚀

## Nopea aloitus

```bash
# 1. Katso tietokannan tilanne
cd /workspaces/kriitikot/src
python3 db_status.py

# 2. Importoi 2 uutta arvostelua jokaisesta lähteestä
python3 quick_import.py

# 3. Käynnistä web-sovellus
python3 app.py
# Avaa http://localhost:5000
```

## Tietokannan päivitys

```bash
# Katso nykyinen tilanne
cd /workspaces/kriitikot/src
python3 db_status.py

# Päivitä tietokanta (kaikki lähteet, 5 arvostelua)
python3 batch_update.py

# Päivitä vain HS
python3 batch_update.py --source hs --limit 10

# Täysi päivitys
python3 batch_update.py --full
```

## Testaus

```bash
# Testaa kaikki scrapers
pytest tests/test_scraper.py -v

# Testaa vain HS
pytest tests/test_scraper.py::test_hs_scraper_basic -v
```

## Discovery-testaus

```bash
# Testaa HS discovery
python3 -c "
from discovery import MetaScraper
meta = MetaScraper()
meta.preview_discoveries('hs', count=5)
"

# Testaa kaikki lähteet
cd src
python3 discovery.py
```

## Web-sovellus

```bash
# Käynnistä Flask
cd src
python3 app.py

# Avaa selaimessa: http://localhost:5000
```

## Cron-asennus (päivittäinen päivitys klo 08:00)

```bash
crontab -e

# Lisää rivi:
0 8 * * * /workspaces/kriitikot/src/run_batch_update.sh daily
```

## Backup

```bash
# Manuaalinen backup
cp /workspaces/kriitikot/reviews.db /backups/reviews_$(date +%Y%m%d).db

# Tarkista backupit
ls -lh /workspaces/kriitikot/backups/
```

## Lokit

```bash
# Katso viimeisimpiä lokeja
ls -lht /workspaces/kriitikot/logs/ | head -5

# Seuraa viimeisintä lokia
tail -f /workspaces/kriitikot/logs/batch_update_*.log
```

## Ongelmatilanteet

### Tietokanta lukittu
```bash
# Pysäytä Flask ja yritä uudelleen
pkill -f "python.*app.py"
python3 batch_update.py
```

### Scraper ei toimi
```bash
# Testaa yksittäinen URL
python3 -c "
from scraper import HSScraper
import requests

url = 'https://www.hs.fi/taide/art-XXXXXXXX.html'
html = requests.get(url).text
review = HSScraper().parse_html(html, url)
print(review)
"
```

### Discovery ei löydä arvosteluja
```bash
# Testaa discovery erikseen
python3 -c "
from discovery import CategoryCrawler
crawler = CategoryCrawler()
reviews = crawler.find_review_links('hs', limit=10)
for r in reviews:
    print(r['title'])
"
```
