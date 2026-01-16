"""
Discovery-moduuli: Löytää uudet elokuva-arvostelut automaattisesti.

Tämä moduuli sisältää "metascraperin" joka:
1. Crawlaa kategoriasivuja ja JSON-API:ta
2. Tunnistaa arvostelut
3. Palauttaa URL-listoja jatkokäsittelyä varten

Tuetut lähteet:
- HS: Next.js JSON (hs.fi/aihe/elokuvat/)
- TS: HTML category page (ts.fi/kulttuuri/)
- IL: JSON API (iltalehti.fi/tv-ja-leffat)
- KSML: HTML search page (ksml.fi/haku/)
- SK: HTML category page (suomenkuvalehti.fi/avainsana/elokuva/)
- IS: Next.js JSON (is.fi/tv-ja-elokuvat/)
- EPISODI: WordPress JSON API (episodi.fi/wp-json/wp/v2/elokuvat)
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
import re
import json
from datetime import datetime


class CategoryCrawler:
    """Crawlaa kategoriasivuja ja löytää linkejä arvosteluihin."""
    
    # Kategoriasivut joilta arvostelut löytyvät
    CATEGORY_PAGES = {
        'sk': 'https://suomenkuvalehti.fi/avainsana/elokuva/',
        'hs': 'https://www.hs.fi/aihe/elokuvat/',
        'ts': 'https://www.ts.fi/kulttuuri/',
        'il': 'https://www.iltalehti.fi/tv-ja-leffat',
        'ksml': 'https://www.ksml.fi/haku/?q=Elokuva-arvio',
        'is': 'https://www.is.fi/tv-ja-elokuvat/',
        'episodi': 'https://www.episodi.fi/wp-json/wp/v2/elokuvat',
        'muropaketti': 'https://muropaketti.com/kategoria/elokuvat/elokuva-arvostelut/',
        'filmoholic': 'https://www.film-o-holic.com/arvostelut/',
        'filmoholic': 'https://www.film-o-holic.com/arvostelut/',
        'kulttuuritoimitus': 'https://www.kulttuuritoimitus.fi/wp-json/wp/v2/posts?categories=11',
        'seura': 'https://seura.fi/tv/',
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def find_review_links(self, source: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Palauttaa arvostelu-URL:t kategoriasivulta.
        
        Args:
            source: Lähteen tunniste ('sk', 'hs', 'ts', 'il', 'ksml', 'is', 'episodi', 'muropaketti', 'filmoholic', 'kulttuuritoimitus')
            limit: Montako arvostelua max palautetaan
            
        Returns:
            Lista dictionaryja, joissa 'title' ja 'url'
        """
        url = self.CATEGORY_PAGES.get(source)
        if not url:
            raise ValueError(f"Unknown source: {source}")
        
        # Episodi ja Kulttuuritoimitus käyttävät JSON API:a suoraan
        if source == 'episodi':
            return self._find_episodi_reviews_json(url, limit)
        
        if source == 'kulttuuritoimitus':
            return self._find_kulttuuritoimitus_reviews_json(url, limit)
        
        # Lähdekohtainen logiikka
        if source == 'sk':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_sk_reviews(soup, limit)
        
        elif source == 'hs':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_hs_reviews(soup, limit)
        
        elif source == 'ts':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_ts_reviews(soup, limit)
        
        elif source == 'il':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_il_reviews(soup, url)
        
        elif source == 'ksml':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_ksml_reviews(soup, limit)
        
        elif source == 'is':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_is_reviews(soup, limit)
        
        elif source == 'muropaketti':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_muropaketti_reviews(soup, limit)
        
        elif source == 'filmoholic':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_filmoholic_reviews(soup, limit)
        
        elif source == 'seura':
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, 'html.parser')
            return self._find_seura_reviews(soup, limit)
        
        return []
    
    def _find_sk_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Suomen Kuvalehden arvostelut."""
        reviews = []
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            
            # SK:n arvostelut alkavat "Arvio:"
            if text.startswith('Arvio:'):
                url = link['href']
                
                # Muodosta absoluuttinen URL
                if url.startswith('/'):
                    url = 'https://suomenkuvalehti.fi' + url
                
                reviews.append({
                    'title': text,
                    'url': url
                })
                
                if len(reviews) >= limit:
                    break
        
        return reviews
    
    def _find_hs_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Helsingin Sanomien arvostelut Next.js JSON:sta.
        HS.fi käyttää Next.js:ää ja artikkeli-data on <script id="__NEXT_DATA__"> tagissa.
        """
        reviews = []
        
        # Etsi __NEXT_DATA__ script tag
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not next_data_script:
            return reviews
        
        try:
            # Parsitaan JSON
            data = json.loads(next_data_script.string)
            
            # Navigoidaan: props.pageProps.page.data.data[].lanes[].items[]
            page_props = data.get('props', {}).get('pageProps', {})
            page = page_props.get('page', {})
            page_data_wrapper = page.get('data', {})
            page_data = page_data_wrapper.get('data', [])
            
            # Käy läpi kaikki lanes ja items
            for data_item in page_data:
                lanes = data_item.get('lanes', [])
                for lane in lanes:
                    items = lane.get('items', [])
                    for item in items:
                        # Tarkista onko tämä elokuva-arvio
                        story_logo = item.get('storyLogo', '')
                        if story_logo == 'Elokuva-arvio':
                            title = item.get('title', '').strip()
                            url_path = item.get('url', '').strip()
                            
                            if title and url_path:
                                # Muodosta absoluuttinen URL
                                if url_path.startswith('/'):
                                    url = 'https://www.hs.fi' + url_path
                                else:
                                    url = 'https://www.hs.fi/' + url_path
                                
                                reviews.append({
                                    'title': title,
                                    'url': url
                                })
                                
                                if len(reviews) >= limit:
                                    return reviews
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  [HS] JSON parsing error: {e}")
            return reviews
        
        return reviews
    
    def _find_ts_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Turun Sanomien arvostelut kategoriasivulta."""
        reviews = []
        
        # TS käyttää <span>Elokuva-arvostelu</span> tageja
        for tag in soup.find_all('span', string='Elokuva-arvostelu'):
            # Etsi lähimmän <a> elementin
            article_div = tag.find_parent('div', class_='article')
            if article_div:
                # Hae article ID
                article_id = article_div.get('data-articleid')
                
                # Hae otsikko
                header = article_div.find('span', class_='header')
                if header and article_id:
                    title = header.get_text(strip=True)
                    url = f'https://www.ts.fi/kulttuuri/{article_id}'
                    
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        return reviews
    
    def _find_il_reviews(self, soup, base_url):
        """Find IL movie reviews from embedded JSON data"""
        reviews = []
        
        # IL embeds article data in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '"headline"' in script.string and 'IL-arvio' in script.string:
                try:
                    # Try to extract article data from JSON
                    # Look for patterns like: "article_id":"xxx"..."headline":"IL-arvio: ..."
                    import re
                    
                    # Tarkempi pattern: article_id tulee ennen headlinea samassa objektissa
                    # Haetaan max 200 merkkiä article_id:n ja headline:n väliltä
                    article_pattern = r'"article_id":"([a-f0-9-]+)"[^}]{0,200}?"headline":"(IL-arvio[^"]+)"'
                    matches = re.findall(article_pattern, script.string)
                    
                    for article_id, headline in matches:
                        # Varmista että article_id on UUID-muotoinen
                        if '-' in article_id and len(article_id) > 30:
                            url = f"https://www.iltalehti.fi/tv-ja-leffat/a/{article_id}"
                            reviews.append({
                                'title': headline.strip(),
                                'url': url
                            })
                            
                            # Limit to a few reviews
                            if len(reviews) >= 5:
                                break
                except Exception as e:
                    print(f"  [IL] JSON parsing error: {e}")
                    continue
        
        return reviews
    
    def _find_is_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Ilta-Sanomien arvostelut Next.js JSON:sta.
        IS.fi käyttää Next.js:ää, artikkeli-data on <script id="__NEXT_DATA__"> tagissa.
        Elokuva-arviot tunnistetaan byLine-kentästä (kriitikot kuten "Taneli Topelius").
        
        HUOM: Hylkää TV-arvostelut ("Tänään tv:ssä") ja suoratoistoarvostelut.
        """
        reviews = []
        
        # Etsi __NEXT_DATA__ script tag
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not next_data_script:
            return reviews
        
        try:
            # Parsitaan JSON
            data = json.loads(next_data_script.string)
            
            # IS.fi:n rakenne: props.pageProps.page.data.data[].lanes[].items[]
            page_props = data.get('props', {}).get('pageProps', {})
            page = page_props.get('page', {})
            page_data_wrapper = page.get('data', {})
            page_data = page_data_wrapper.get('data', [])
            
            # Tunnetut IS.fi:n elokuvakriitikot
            known_critics = ['Taneli Topelius', 'Pekka Eronen', 'Pauliina Leinonen', 'Jouko Juutilainen', 'Tarmo Poussu']
            
            # Hylättävät otsikkopatternit (TV-arvostelut)
            excluded_patterns = [
                'tänään tv:ssä',
                'tänään tv',
                'katso ilmaiseksi',
                'katsomo+',
                'netflix',
                'viaplay',
                'hbo',
                'suoratoistossa',
                'illalla tv:ssä',
                'tv-vinkki',
                'valitse katsottavaksi'
            ]
            
            # Arvosteluun viittaavat avainsanat
            review_keywords = [
                'tähden arvoinen', 'elokuva', 'arvio', 'arvostelu', 
                'leffassa', 'leffa', 'ensi-ilta', 'ensi-illassa', 
                'valkokanka', 'teattereissa', 'komedia', 'traileri'
            ]
            
            # Käy läpi kaikki lanes ja items. IS on usein satoja artikkeleita JSONissa.
            for data_item in page_data:
                lanes = data_item.get('lanes', [])
                for lane in lanes:
                    items = lane.get('items', [])
                    for item in items:
                        # Tarkista onko byLine (kriitikko) tiedossa
                        byline = item.get('byLine', '').strip()
                        title = item.get('title', '').strip()
                        url_path = item.get('url', '').strip()
                        ingress = item.get('ingress', '').strip().lower()
                        
                        if not title or not url_path:
                            continue
                            
                        # Jos kriitikko on tunnettu JA otsikossa tai ingressissä viitteitä arvioon
                        if byline in known_critics:
                            title_lower = title.lower()
                            
                            # Hylkää selkeät TV-vinkit
                            if any(pattern in title_lower for pattern in excluded_patterns):
                                continue
                            
                            # Tarkistetaan sekä otsikko että ingress
                            found_keyword = False
                            if any(kw in title_lower for kw in review_keywords):
                                found_keyword = True
                            elif any(kw in ingress for kw in review_keywords):
                                found_keyword = True
                            
                            if found_keyword:
                                # Muodosta absoluuttinen URL
                                if url_path.startswith('/'):
                                    url = 'https://www.is.fi' + url_path
                                else:
                                    url = 'https://www.is.fi/' + url_path
                                
                                reviews.append({
                                    'title': title,
                                    'url': url
                                })
                                
                                if len(reviews) >= limit:
                                    return reviews
        
        except json.JSONDecodeError as e:
            print(f"Virhe JSON parsinnassa: {e}")
        except Exception as e:
            print(f"Virhe IS.fi arvostelujen etsinnässä: {e}")
        
        return reviews
    
    def _find_ksml_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Keskisuomalaisen arvostelut hakusivulta."""
        reviews = []
        
        # KSML käyttää hakua, etsitään artikkeleita
        for link in soup.find_all('a', href=True):
            # Tarkista onko linkki artikkelin otsikko
            href = link.get('href', '')
            
            # KSML:n artikkelit ovat muotoa /kulttuuri/{id} tai /paikalliset/{id}
            if '/kulttuuri/' in href or '/paikalliset/' in href:
                # Tarkista onko "Elokuva-arvio" lähellä
                parent = link.find_parent('article') or link.find_parent('div', class_='article')
                if parent:
                    text_content = parent.get_text()
                    if 'Elokuva-arvio' in text_content:
                        title = link.get_text(strip=True)
                        url = href
                        
                        # Muodosta absoluuttinen URL
                        if url.startswith('/'):
                            url = 'https://www.ksml.fi' + url
                        
                        reviews.append({
                            'title': title,
                            'url': url
                        })
                        
                        if len(reviews) >= limit:
                            break
        
        return reviews
    
    def _find_muropaketti_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Muropaketin elokuva-arvostelut.
        
        Muropaketin arvostelut ovat kategoriasivulla linkkinä jossa on 
        class="category-name" span jossa lukee "Arvostelu" tai "Arvio".
        """
        reviews = []
        
        # Etsi kaikki linkit joiden sisällä on <span class="category-name">
        for link in soup.find_all('a', href=True):
            category_span = link.find('span', class_='category-name')
            if category_span:
                category_text = category_span.get_text().strip()
                
                # Tarkista että on arvostelu tai arvio
                if category_text in ['Arvostelu', 'Arvio']:
                    url = link['href']
                    
                    # Muodosta absoluuttinen URL
                    if url.startswith('/'):
                        url = 'https://muropaketti.com' + url
                    
                    # Otsikko on koko linkin tekstistä ilman category-spanin tekstiä
                    full_text = link.get_text(strip=True)
                    # Poista "Arvostelu " tai "Arvio " alusta
                    title = full_text.replace(category_text, '').strip()
                    
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        return reviews
    
    def _find_filmoholic_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Film-O-Holic arvostelut kategoriasivulta.
        
        Film-O-Holic arvostelut ovat <ul class="article-list"> -listassa,
        jossa on <li> elementtejä joiden sisällä on linkki arvosteluun.
        """
        reviews = []
        
        # Etsi article-list
        article_list = soup.find('ul', class_='article-list')
        if not article_list:
            return reviews
        
        # Käy läpi kaikki linkit jotka osoittavat /arvostelut/-polkuun
        for link in article_list.find_all('a', href=True):
            href = link['href']
            
            # Tarkista että linkki on arvostelu (ei filtterit kuten ?grade=5)
            if href.startswith('/arvostelut/') and '?' not in href:
                # Otsikko on h4-tagissa
                h4 = link.find('h4')
                if not h4:
                    continue
                
                title = h4.get_text(strip=True)
                
                # Muodosta absoluuttinen URL
                url = 'https://www.film-o-holic.com' + href
                
                if title and url:
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        return reviews
    
    def _find_seura_reviews(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, str]]:
        """Löytää Seura.fi:n arvostelut /tv/ -sivulta."""
        reviews = []
        
        # Etsi kaikki linkit
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']
            
            # Arvostelut alkavat usein "Elokuva-arvio:"
            if text.startswith('Elokuva-arvio:'):
                title = text.replace('Elokuva-arvio:', '').strip()
                url = href
                
                # Muodosta absoluuttinen URL tarvittaessa
                if url.startswith('/'):
                    url = 'https://seura.fi' + url
                    
                reviews.append({
                    'title': title,
                    'url': url
                })
                
                if len(reviews) >= limit:
                    break
            
            # Tai jos URL sisältää "elokuva-arvio" ja teksti on järkevä
            elif 'elokuva-arvio' in href and len(text) > 10:
                title = text
                if title.startswith('Elokuva-arvio:'):
                    title = title.replace('Elokuva-arvio:', '').strip()
                
                url = href
                if url.startswith('/'):
                    url = 'https://seura.fi' + url
                
                # Vältä duplikaatteja
                if not any(r['url'] == url for r in reviews):
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break

        return reviews
    
    def _find_kulttuuritoimitus_reviews_json(self, api_url: str, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Kulttuuritoimitus.fi:n elokuva-arvostelut WordPress JSON API:sta.
        
        API URL sisältää jo category=11 (Elokuvakritiikki) parametrin.
        """
        reviews = []
        
        try:
            response = requests.get(
                api_url,
                params={'per_page': limit, 'orderby': 'date', 'order': 'desc', '_embed': '1'},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            for item in data:
                # Title on rendered HTML, puhdistetaan
                title_obj = item.get('title', {})
                if isinstance(title_obj, dict):
                    title = title_obj.get('rendered', '').strip()
                else:
                    title = str(title_obj).strip()
                
                # Poista HTML-tagit otsikosta
                from bs4 import BeautifulSoup
                title_soup = BeautifulSoup(title, 'html.parser')
                title = title_soup.get_text(strip=True)
                
                url = item.get('link', '')
                
                if title and url:
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        except Exception as e:
            print(f"  [Kulttuuritoimitus] JSON API virhe: {e}")
        
        return reviews
    
    def _find_episodi_reviews_json(self, api_url: str, limit: int) -> List[Dict[str, str]]:
        """
        Löytää Episodi.fi:n arvostelut WordPress JSON API:sta.
        """
        reviews = []
        
        try:
            response = requests.get(
                api_url,
                params={'per_page': limit, 'orderby': 'date', 'order': 'desc', '_embed': '1'},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            for item in data:
                title = item.get('title', {}).get('rendered', '').strip()
                url = item.get('link', '')
                
                if title and url:
                    reviews.append({
                        'title': title,
                        'url': url
                    })
                    
                    if len(reviews) >= limit:
                        break
        
        except Exception as e:
            print(f"  [Episodi] JSON API virhe: {e}")
        
        return reviews
    
    def _fetch_url(self, url: str) -> str:
        """Hakee URL:n sisällön."""
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.text


class MetaScraper:
    """
    Pääorchestraattori joka koordinoi arvostelujen löytämistä.
    
    Yhdistää category crawlerin ja yksittäisten arvostelujen scrapauksen.
    """
    
    def __init__(self):
        self.category_crawler = CategoryCrawler()
    
    def discover_new_reviews(self, source: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Löytää uudet arvostelut lähteestä.
        
        Args:
            source: Lähteen tunniste ('sk', 'hs', 'ts', 'il', 'ksml', 'is', 'episodi', 'muropaketti')
            limit: Montako max arvostelua etsitään
            
        Returns:
            Lista arvosteluja: [{'title': '...', 'url': '...'}]
        """
        print(f"🔍 Etsitään arvosteluja lähteestä: {source.upper()}")
        
        reviews = self.category_crawler.find_review_links(source, limit)
        
        print(f"✅ Löytyi {len(reviews)} arvostelua")
        
        return reviews
    
    def preview_discoveries(self, source: str, count: int = 5):
        """Näyttää preview löydetyistä arvosteluista."""
        reviews = self.discover_new_reviews(source, limit=count)
        
        print(f"\n📰 {source.upper()} - Uusimmat arvostelut:\n")
        
        for i, review in enumerate(reviews, 1):
            print(f"{i}. {review['title'][:70]}...")
            print(f"   🔗 {review['url']}")
            print()


# Esimerkki käytöstä
if __name__ == '__main__':
    print("=" * 60)
    print("METASCRAPER - Arvostelujen etsintä")
    print("=" * 60)
    print()
    
    meta = MetaScraper()
    
    # Testaa kaikki lähteet
    for source in ['hs', 'ts', 'il', 'ksml', 'sk', 'is', 'episodi', 'muropaketti']:
        try:
            print(f"\n{'='*60}")
            meta.preview_discoveries(source, count=3)
        except Exception as e:
            print(f"❌ Virhe lähteessä {source}: {e}")
    
    print("\n💡 Käyttö:")
    print("   from discovery import MetaScraper")
    print("   meta = MetaScraper()")
    print("   reviews = meta.discover_new_reviews('ts', limit=10)")
    print()
