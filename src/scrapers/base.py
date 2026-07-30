"""
Base classes for movie review scrapers.

Provides common data structures and abstract base class for all scrapers.
"""

import json
import re
from typing import Optional, Dict, Any, Sequence
from bs4 import BeautifulSoup


class Review:
    """Yhtenäinen tietorakenne arvostelulle, riippumaton lähteestä."""
    
    def __init__(
        self,
        movie_title: str,
        critic_name: str,
        rating_stars: Optional[int] = None,
        review_text: Optional[str] = None,
        source_url: Optional[str] = None,
        source_publication: str = "Unknown",
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.movie_title = movie_title
        self.critic_name = critic_name
        self.rating_stars = rating_stars  # 1-5 tähteä tai None
        self.review_text = review_text
        self.source_url = source_url
        self.source_publication = source_publication
        self.raw_data = raw_data or {}
    
    def to_dict(self) -> dict:
        """Palauttaa arvostelun sanakirjana."""
        return {
            'movie_title': self.movie_title,
            'critic_name': self.critic_name,
            'rating_stars': self.rating_stars,
            'review_text': self.review_text,
            'source_url': self.source_url,
            'source_publication': self.source_publication
        }


class BaseScraper:
    """Abstract base class for all scrapers."""

    # Tähtisymbolit joita julkaisut käyttävät (⭐ = emoji, ★ = musta tähti)
    STAR_CHARS = '★⭐'

    # Suomalaiset lukusanat arvosanoissa ("neljä tähteä", "neljän tähden")
    FINNISH_NUMERALS = {
        'yksi': 1, 'yhden': 1,
        'kaksi': 2, 'kahden': 2,
        'kolme': 3, 'kolmen': 3,
        'neljä': 4, 'neljän': 4,
        'viisi': 5, 'viiden': 5,
    }

    # Yleisimmät artikkelisisällön kontit, järjestyksessä
    CONTENT_SELECTORS = (
        'article',
        'div.entry-content',
        '.article-body',
        '.article__body',
        '.content-body',
        '.content',
    )

    def __init__(self, publication_name: str):
        self.publication_name = publication_name

    # --- Jaetut poimintaapurit ---------------------------------------------

    def count_stars(self, text: str, max_stars: int = 5) -> Optional[int]:
        """Laske tähtisymbolit tekstistä.

        Returns:
            Tähtien määrä (1..max_stars) tai None jos tähtiä ei ole.
        """
        if not text:
            return None

        count = sum(text.count(char) for char in self.STAR_CHARS)
        if count <= 0:
            return None
        return min(count, max_stars)

    def parse_rating(self, text: str, max_stars: int = 5) -> Optional[int]:
        """Poimi arvosana tekstistä useilla eri tavoilla.

        Kokeilee järjestyksessä:
        1. Peräkkäiset tähtisymbolit (★★★★)
        2. "X/5"
        3. "X tähteä" / "X tähden"
        4. Suomalainen lukusana + tähti ("neljä tähteä")
        """
        if not text:
            return None

        # 1. Peräkkäiset tähdet
        star_run = re.search(rf'([{self.STAR_CHARS}]{{1,{max_stars}}})', text)
        if star_run:
            return len(star_run.group(1))

        # 2. X/5
        fraction = re.search(rf'\b([1-{max_stars}])\s*/\s*{max_stars}\b', text)
        if fraction:
            return int(fraction.group(1))

        lowered = text.lower()

        # Kattaa taivutusmuodot tähteä / tähden / tähti / tähtiä,
        # mutta ei sanaa "tähän"
        star_word = r'täh[dt][eiä]'

        # 3. "4 tähteä"
        numeric = re.search(rf'\b([1-{max_stars}])\s*{star_word}', lowered)
        if numeric:
            return int(numeric.group(1))

        # 4. "neljä tähteä"
        if re.search(star_word, lowered):
            for word, num in self.FINNISH_NUMERALS.items():
                if re.search(rf'\b{word}\b', lowered):
                    return num

        return None

    def extract_jsonld(self, soup: BeautifulSoup,
                       types: Sequence[str] = ('NewsArticle', 'Article', 'Review')) -> Optional[dict]:
        """Etsi ensimmäinen ld+json-lohko joka vastaa annettuja @type-arvoja.

        Käsittelee kaikki kolme yleistä muotoa: pelkkä dict, lista ja @graph.
        """
        def matches(item):
            if not isinstance(item, dict):
                return False
            item_type = item.get('@type')
            if isinstance(item_type, list):
                return any(t in types for t in item_type)
            return item_type in types

        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            try:
                data = json.loads(script.string or '{}')
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = []
            if isinstance(data, list):
                candidates = data
            elif isinstance(data, dict):
                if '@graph' in data and isinstance(data['@graph'], list):
                    candidates = data['@graph']
                else:
                    candidates = [data]

            for item in candidates:
                if matches(item):
                    return item

        return None

    def extract_author(self, soup: BeautifulSoup, ld_json: Optional[dict] = None,
                       exclude: Sequence[str] = ()) -> Optional[str]:
        """Poimi kirjoittajan nimi metatiedoista tai JSON-LD:stä.

        Args:
            exclude: Nimet jotka hylätään (esim. julkaisun oma nimi).
        """
        excluded = {name.lower() for name in exclude}

        def accept(name):
            if not name:
                return None
            name = name.strip()
            if not name or name.lower() in excluded:
                return None
            return name

        # 1. <meta property="article:author">
        meta_author = soup.find('meta', property='article:author')
        if meta_author and meta_author.get('content'):
            if (name := accept(meta_author['content'])):
                return name

        # 2. JSON-LD author (dict, lista tai merkkijono)
        if ld_json:
            author = ld_json.get('author')
            if isinstance(author, list):
                author = author[0] if author else None
            if isinstance(author, dict):
                author = author.get('name')
            if isinstance(author, str):
                if (name := accept(author)):
                    return name

        # 3. <meta name="author">
        meta_name = soup.find('meta', attrs={'name': 'author'})
        if meta_name and meta_name.get('content'):
            if (name := accept(meta_name['content'])):
                return name

        # 4. rel="author"
        rel_author = soup.find(attrs={'rel': 'author'})
        if rel_author:
            if (name := accept(rel_author.get_text(strip=True))):
                return name

        return None

    def meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """og:description tai meta[name=description]."""
        for finder in (lambda: soup.find('meta', property='og:description'),
                       lambda: soup.find('meta', attrs={'name': 'description'})):
            meta = finder()
            if meta and meta.get('content'):
                text = meta['content'].strip()
                if text:
                    return text
        return None

    def extract_next_data(self, soup: BeautifulSoup) -> Optional[dict]:
        """Parsi Next.js <script id="__NEXT_DATA__"> -lohko."""
        script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script or not script.string:
            return None
        try:
            return json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            return None

    def extract_paragraphs(self, soup: BeautifulSoup, *,
                           selectors: Optional[Sequence[str]] = None,
                           min_length: int = 30,
                           skip_phrases: Sequence[str] = (),
                           skip_parent_classes: Sequence[str] = (),
                           separator: str = ' ',
                           max_chars: Optional[int] = None,
                           limit: Optional[int] = None) -> Optional[str]:
        """Poimi artikkelin leipäteksti <p>-tageista.

        Args:
            selectors: Sisältökontit joita kokeillaan järjestyksessä.
            min_length: Tätä lyhyemmät kappaleet ohitetaan.
            skip_phrases: Kappale ohitetaan jos se alkaa/sisältää näitä.
            skip_parent_classes: Ohita kappaleet joiden esivanhemmalla on tämä luokka.
            separator: Kappaleiden yhdistäjä.
            max_chars: Katkaise tulos tähän pituuteen.
            limit: Ota korkeintaan näin monta kappaletta.
        """
        selectors = selectors or self.CONTENT_SELECTORS
        skip_lower = [phrase.lower() for phrase in skip_phrases]

        container = None
        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                break

        if not container:
            return None

        collected = []
        for p in container.find_all('p'):
            if skip_parent_classes:
                blocked = False
                for parent in p.parents:
                    parent_classes = parent.get('class') or []
                    if any(cls in parent_classes for cls in skip_parent_classes):
                        blocked = True
                        break
                if blocked:
                    continue

            text = p.get_text(strip=True)
            if len(text) < min_length:
                continue

            lowered = text.lower()
            if any(phrase in lowered for phrase in skip_lower):
                continue

            collected.append(text)
            if limit and len(collected) >= limit:
                break

        if not collected:
            return None

        result = separator.join(collected)
        if max_chars and len(result) > max_chars:
            result = result[:max_chars]
        return result

    def get_soup(self, html_content: str) -> BeautifulSoup:
        """
        Create BeautifulSoup object from HTML content.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html_content, 'html.parser')
    
    def parse_html(self, html_content: str, source_url: Optional[str] = None) -> Optional[Review]:
        """
        Parse HTML content and return a Review object.
        
        Args:
            html_content: HTML content as string
            source_url: Original URL (optional)
            
        Returns:
            Review object or None if parsing fails
        """
        raise NotImplementedError("Subclasses must implement parse_html()")
    
    def parse_file(self, filepath: str) -> Optional[Review]:
        """
        Parse HTML from file and return a Review object.
        
        Args:
            filepath: Path to HTML file
            
        Returns:
            Review object or None if parsing fails
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return self.parse_html(html_content)
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            return None
