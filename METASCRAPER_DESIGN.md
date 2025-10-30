# Metascraper - Arkkitehtuurisuunnitelma

## Ongelma
Miten löydämme automaattisesti uudet elokuva-arvostelut ilman manuaalista URL-syöttöä?

## Ratkaisu 1: RSS/Atom Feed Crawler (SUOSITUS ⭐)

### Toimintaperiaate
Useimmat uutissivustot julkaisevat RSS-feedejä eri kategorioille.

### Toteutus
```python
import feedparser
from datetime import datetime, timedelta

class FeedCrawler:
    """Seuraa RSS-feedejä ja löytää uudet arvostelut."""
    
    FEEDS = {
        'hs': 'https://www.hs.fi/rss/kulttuuri.xml',
        'ksml': 'https://www.ksml.fi/rss/kulttuuri',
        'il': 'https://www.iltalehti.fi/rss/viihde.xml',
        'ts': 'https://www.ts.fi/rss/kulttuuri.xml'
    }
    
    def find_new_reviews(self, source: str, since: datetime) -> List[str]:
        """Palauttaa listan uusien arvostelujen URL:eja."""
        feed_url = self.FEEDS.get(source)
        feed = feedparser.parse(feed_url)
        
        review_urls = []
        for entry in feed.entries:
            # Tarkista onko elokuva-arvostelu
            if self._is_movie_review(entry):
                # Tarkista onko uusi
                pub_date = datetime(*entry.published_parsed[:6])
                if pub_date > since:
                    review_urls.append(entry.link)
        
        return review_urls
    
    def _is_movie_review(self, entry) -> bool:
        """Tunnistaa onko kyseessä elokuva-arvostelu."""
        keywords = ['elokuva', 'arvio', 'arvostelu', 'leffa', 'kritik']
        title = entry.title.lower()
        
        # Tarkista otsikosta
        if any(kw in title for kw in keywords):
            return True
        
        # Tarkista kategorioista
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if any(kw in tag.term.lower() for kw in keywords):
                    return True
        
        return False
```

### Edut
- ✅ Yksinkertainen ja luotettava
- ✅ Ei kuormita palvelimia (RSS tarkoitettu tähän)
- ✅ Reaaliaikainen (feedit päivittyvät nopeasti)
- ✅ Standardoitu formaatti

### Haitat
- ❌ Riippuvainen siitä että sivusto tarjoaa RSS:n
- ❌ Pitää tunnistaa arvostelut muusta sisällöstä

---

## Ratkaisu 2: Kategoriasivujen Crawling

### Toimintaperiaate
Scrapaa kulttuuriosioiden etusivuja ja etsi linkkejä arvosteluihin.

### Toteutus
```python
class CategoryCrawler:
    """Crawlaa kategoriasivuja ja löytää arvostelut."""
    
    CATEGORY_PAGES = {
        'hs': 'https://www.hs.fi/kulttuuri/elokuva/',
        'ksml': 'https://www.ksml.fi/kulttuuri/',
        'il': 'https://www.iltalehti.fi/tv-ja-leffat/',
        'ts': 'https://www.ts.fi/kulttuuri/'
    }
    
    def find_review_links(self, source: str) -> List[str]:
        """Palauttaa arvostelu-URL:t kategoriasivulta."""
        url = self.CATEGORY_PAGES[source]
        html = self._fetch_with_headers(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Etsi kaikki artikkelilinkit
        links = []
        for article in soup.find_all('article'):
            link_elem = article.find('a', href=True)
            if link_elem and self._looks_like_review(article):
                links.append(link_elem['href'])
        
        return links
    
    def _looks_like_review(self, article_elem) -> bool:
        """Heuristiikka: näyttääkö arvostelulta?"""
        text = article_elem.get_text().lower()
        
        # Etsi tähtiä
        if '★' in text or '⭐' in text:
            return True
        
        # Etsi avainsanoja
        if 'arvio' in text or 'arvostelu' in text:
            return True
        
        return False
```

### Edut
- ✅ Toimii vaikka ei RSS:ää
- ✅ Voi löytää myös vanhempia arvosteluja

### Haitat
- ❌ HTML-rakenne voi muuttua
- ❌ Kuormittaa palvelimia enemmän
- ❌ Hitaampi kuin RSS

---

## Ratkaisu 3: Hybridimalli (PARAS KÄYTÄNNÖSSÄ 🏆)

### Toimintaperiaate
Käytetään RSS:ää kun mahdollista, fallback kategoriasivuille.

### Arkkitehtuuri
```python
class MetaScraper:
    """Pääorchestraattori joka koordinoi kaikkea."""
    
    def __init__(self, db_connection):
        self.feed_crawler = FeedCrawler()
        self.category_crawler = CategoryCrawler()
        self.db = db_connection
        
        # Priorisoi RSS:ää
        self.strategy = {
            'hs': 'rss',
            'ksml': 'category',  # Jos ei RSS:ää
            'il': 'rss',
            'ts': 'rss'
        }
    
    def discover_new_reviews(self, source: str) -> List[dict]:
        """Löytää uudet arvostelut ja palauttaa metadatan."""
        # Tarkista koska viimeksi haettu
        last_check = self.db.get_last_crawl_time(source)
        
        # Valitse strategia
        if self.strategy[source] == 'rss':
            urls = self.feed_crawler.find_new_reviews(source, last_check)
        else:
            urls = self.category_crawler.find_review_links(source)
        
        # Suodata pois jo tietokannassa olevat
        new_urls = [url for url in urls if not self.db.review_exists(url)]
        
        return new_urls
    
    def scrape_and_store(self, source: str, url: str):
        """Scrapaa arvostelun ja tallentaa tietokantaan."""
        # Hae HTML
        html = self._fetch_url(url)
        
        # Parsii oikealla scraperilla
        review = scrape_review(html, source=source, source_url=url)
        
        if review:
            # Tallenna tietokantaan
            self.db.save_review(review)
            return True
        
        return False
```

---

## Ratkaisu 4: Sitemap.xml Crawling

### Toimintaperiaate
Useilla sivustoilla on sitemap.xml joka listaa kaikki sivut.

### Toteutus
```python
def parse_sitemap(url: str) -> List[str]:
    """Parsii sitemap.xml ja palauttaa URL:t."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    
    urls = []
    for loc in soup.find_all('loc'):
        url = loc.text
        # Suodata vain kulttuuri/elokuva-sivut
        if '/kulttuuri/' in url or '/elokuva' in url:
            urls.append(url)
    
    return urls

# Esim: https://www.hs.fi/sitemap.xml
```

---

## Suositeltu Toteutus (MVP)

### Vaihe 1: RSS-pohjainen metascraper
1. Luo `src/discovery.py` jossa `FeedCrawler` + `MetaScraper`
2. Käytä `feedparser`-kirjastoa
3. Tallenna viimeisin crawl-aika tietokantaan
4. Aja cron-jobina 1-4 kertaa päivässä

### Vaihe 2: Tietokantataulu crawl-metatiedolle
```sql
CREATE TABLE crawl_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(10),
    last_crawled DATETIME,
    articles_found INT,
    reviews_added INT
);
```

### Vaihe 3: Scheduler
```python
# Esim. APScheduler tai cron
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

@scheduler.scheduled_job('interval', hours=6)
def crawl_all_sources():
    for source in ['hs', 'ksml', 'il', 'ts']:
        meta = MetaScraper(db)
        urls = meta.discover_new_reviews(source)
        
        for url in urls:
            meta.scrape_and_store(source, url)

scheduler.start()
```

---

## Teknologiavalinnat

### Kirjastot
- **feedparser**: RSS/Atom parsintaan
- **APScheduler**: Ajastettuun suoritukseen (Python-natiivi)
- **requests-cache**: Välimuistin välttämiseksi tuplatyötä

### Optimoinnit
1. **Rate limiting**: Älä kuormita palvelimia (1 request / 2s)
2. **User-Agent rotation**: Vältä esto
3. **Retry logic**: Käsittele verkkovirheet
4. **Deduplication**: Älä scrapaa samaa kahdesti

---

## Arkkitehtuurikaavio

```
┌─────────────────────────────────────────────────┐
│           SCHEDULER (cron / APScheduler)        │
└────────────────┬────────────────────────────────┘
                 │ (every 6h)
                 ▼
┌─────────────────────────────────────────────────┐
│              MetaScraper                        │
│  - discover_new_reviews()                       │
│  - scrape_and_store()                           │
└────┬──────────────────────────────────────┬─────┘
     │                                       │
     ▼                                       ▼
┌──────────────┐                    ┌──────────────┐
│ FeedCrawler  │                    │  Category    │
│              │                    │  Crawler     │
│ (RSS feeds)  │                    │  (fallback)  │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       └───────────┬───────────────────────┘
                   │ URLs
                   ▼
         ┌─────────────────────┐
         │  HSScraper          │
         │  KSMLScraper        │
         │  ILScraper          │
         │  TSScraper          │
         └──────────┬──────────┘
                    │ Review objects
                    ▼
         ┌─────────────────────┐
         │   MySQL Database    │
         │   - reviews         │
         │   - crawl_history   │
         └─────────────────────┘
```

---

## Toteutuksen prioriteetti

1. **MVP (Viikko 1)**: RSS FeedCrawler + manuaalinen ajo
2. **V2 (Viikko 2)**: APScheduler + automaattinen ajastus
3. **V3 (Viikko 3)**: Category fallback + heuristiikat
4. **V4 (Tulevaisuus)**: Machine learning arvostelu-tunnistukseen

---

## Testaus

```python
def test_feed_crawler():
    """Testaa RSS-feedin parsintaa."""
    crawler = FeedCrawler()
    
    # Mock feedparser vastaus
    urls = crawler.find_new_reviews('hs', datetime(2025, 10, 1))
    
    assert len(urls) > 0
    assert all(isinstance(url, str) for url in urls)

def test_metascraper_deduplication():
    """Varmista että sama arvio ei tallennu kahdesti."""
    meta = MetaScraper(mock_db)
    
    # Ensimmäinen kerta
    meta.scrape_and_store('hs', 'https://example.com/review')
    
    # Toinen kerta (pitäisi skipata)
    result = meta.scrape_and_store('hs', 'https://example.com/review')
    assert result == False  # Already exists
```

---

## Yhteenveto

**SUOSITUS:** Aloita RSS-pohjaisella FeedCrawler:lla. Se on:
- Yksinkertaisin toteuttaa
- Luotettavin
- Ei kuormita palvelimia
- Reaaliaikaisin

Kun tämä toimii, lisää Category Crawler fallbackina niille sivustoille joilla ei RSS:ää.
