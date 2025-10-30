"""
Discovery Importer - Yhdistää discovery-moduulin ja tietokannan.

Hakee uusia arvosteluja discovery-moduulilla ja tallentaa ne tietokantaan.
"""

from discovery import MetaScraper
from models import get_session, get_engine, Movie, Critic, Publication, Review
from scraper import HSScraper, KSMLScraper, ILScraper, TSScraper, SKScraper
from movie_normalizer import get_canonical_title
from typing import List, Dict
import re


class DiscoveryImporter:
    """
    Yhdistää discovery-moduulin ja tietokannan.
    
    1. Löytää uudet arvostelut discovery-moduulilla
    2. Scrapaa arvostelut oikeilla scrapereilla
    3. Tallentaa tietokantaan (välttää duplikaatit)
    """
    
    def __init__(self):
        self.meta_scraper = MetaScraper()
        self.engine = get_engine()
        self.session = get_session(self.engine)
        
        # Scrapers per source
        self.scrapers = {
            'hs': HSScraper(),
            'ksml': KSMLScraper(),
            'il': ILScraper(),
            'ts': TSScraper(),
            'sk': SKScraper(),
        }
    
    def normalize_movie_title(self, title: str) -> str:
        """
        Normalisoi elokuvan nimen.
        
        Poistaa artikkeliotsikosta turhan tekstin ja palauttaa pelkän elokuvan nimen.
        """
        # Poista soft hyphens
        title = title.replace('\xad', '').replace('­', '')
        
        # Poista "Elokuva-arvio", "IL-arvio" jne. prefixit
        title = re.sub(r'^(Elokuva-arvio\s*\|?\s*|IL-arvio:\s*|Arvio:\s*)', '', title, flags=re.IGNORECASE)
        
        # Jos otsikko sisältää " – ", ota vain elokuvan nimi (ennen viivaa)
        if ' – ' in title:
            title = title.split(' – ')[0].strip()
        
        # Jos otsikko sisältää kriitikon analyysin (esim. "elokuva on...", "tarjoaa..."), poista se
        # Esim: "Sorry, baby on Eva Victorin..." -> "Sorry, baby"
        patterns = [
            r'\s+on\s+[A-ZÄÖÅ].*$',  # "on Eva Victorin..."
            r'\s+tekee\s+.*$',        # "tekee loistoroolin..."
            r'\s+tarjoaa\s+.*$',      # "tarjoaa..."
            r'\s+olisi\s+.*$',        # "olisi ansainnut..."
            r'\s+vie\s+.*$',          # "vie katsojan..."
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                title = title[:match.start()].strip()
                break
        
        # Poista loppupisteen jälkeinen teksti jos sellainen on
        if '.' in title:
            # Mutta vain jos se ei ole lyhenne (esim. "Dr.")
            parts = title.split('.')
            if len(parts) > 1 and len(parts[-1]) > 20:
                # Pitkä loppuosa, todennäköisesti selitys
                title = '.'.join(parts[:-1]).strip()
        
        # Rajoita pituutta (max 100 merkkiä)
        if len(title) > 100:
            # Etsi viimeinen välilyönti ennen 100 merkkiä
            truncated = title[:100]
            last_space = truncated.rfind(' ')
            if last_space > 50:  # Varmista ettei ole liian lyhyt
                title = truncated[:last_space]
        
        return title.strip()
    
    def get_or_create_movie(self, title: str) -> Movie:
        """
        Hakee tai luo elokuvan fuzzy matchingilla.
        
        Etsii ensin vastaavan elokuvan tietokannasta (90% samankaltaisuus).
        Jos löytyy, käyttää olemassa olevaa nimeä.
        Muuten luo uuden elokuvan.
        """
        normalized = self.normalize_movie_title(title)
        
        # Hae kaikki elokuvien nimet tietokannasta
        existing_movies = self.session.query(Movie).all()
        existing_titles = [m.title for m in existing_movies]
        
        # Etsi vastaava nimi fuzzy matchingilla (90% samankaltaisuus)
        canonical_title = get_canonical_title(normalized, existing_titles, threshold=0.9)
        
        # Hae tai luo elokuva kanonisella nimellä
        movie = self.session.query(Movie).filter_by(title=canonical_title).first()
        if not movie:
            movie = Movie(title=canonical_title)
            self.session.add(movie)
            self.session.flush()
            print(f"   🎬 Luotiin uusi elokuva: {canonical_title}")
        elif canonical_title != normalized:
            # Löytyi vastaava, käytetään olemassa olevaa
            print(f"   🔗 Yhdistetty olemassa olevaan: {canonical_title}")
        return movie
    
    def get_or_create_critic(self, name: str, media: str = None) -> Critic:
        """Hakee tai luo kriitikon."""
        critic = self.session.query(Critic).filter_by(name=name).first()
        if not critic:
            critic = Critic(name=name, media=media)
            self.session.add(critic)
            self.session.flush()
            print(f"   ✍️  Luotiin uusi kriitikko: {name}")
        elif media and not critic.media:
            # Päivitä media jos puuttuu
            critic.media = media
            self.session.flush()
        return critic
    
    def get_publication(self, short_name: str) -> Publication:
        """Hakee julkaisun."""
        return self.session.query(Publication).filter_by(short_name=short_name).first()
    
    def import_discovered_reviews(self, source: str, limit: int = 10) -> int:
        """
        Löytää ja importoi uudet arvostelut lähteestä.
        
        Args:
            source: Lähteen tunniste ('hs', 'ksml', 'il', 'ts', 'sk')
            limit: Montako max arvostelua etsitään
            
        Returns:
            Importoitujen arvostelujen määrä
        """
        print(f"\n{'='*60}")
        print(f"🔍 IMPORT: {source.upper()}")
        print(f"{'='*60}\n")
        
        # 1. Löydä uudet arvostelut
        discovered = self.meta_scraper.discover_new_reviews(source, limit)
        print(f"✅ Löydettiin {len(discovered)} arvostelua\n")
        
        if not discovered:
            print("⚠️  Ei uusia arvosteluja\n")
            return 0
        
        # 2. Scrape ja tallenna
        scraper = self.scrapers.get(source)
        if not scraper:
            print(f"❌ Ei scraperia lähteelle: {source}")
            return 0
        
        publication = self.get_publication(source)
        if not publication:
            print(f"❌ Julkaisua ei löydy tietokannasta: {source}")
            return 0
        
        imported = 0
        skipped = 0
        failed = 0
        
        for i, discovery in enumerate(discovered, 1):
            url = discovery['url']
            title_preview = discovery['title'][:60]
            
            print(f"\n[{i}/{len(discovered)}] {title_preview}...")
            print(f"   🔗 {url}")
            
            # Tarkista onko jo tietokannassa
            existing = self.session.query(Review).filter_by(source_url=url).first()
            if existing:
                print(f"   ⏭️  Jo tietokannassa")
                skipped += 1
                continue
            
            # Scrape arvostelu
            try:
                # Lataa HTML ja parsea
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html = response.text
                
                review = scraper.parse_html(html, url)
                if not review:
                    print(f"   ❌ Scraping epäonnistui")
                    failed += 1
                    continue
                
                # Luo relaatiot
                movie = self.get_or_create_movie(review.movie_title)
                critic = self.get_or_create_critic(review.critic_name, media=source.upper())
                
                # Tallenna arvostelu
                db_review = Review(
                    movie=movie,
                    critic=critic,
                    publication=publication,
                    rating_stars=review.rating_stars,
                    review_text=review.review_text,
                    source_url=review.source_url
                )
                
                self.session.add(db_review)
                self.session.commit()
                
                imported += 1
                print(f"   ✅ Tallennettu: {movie.title} - {critic.name} - {review.rating_stars}★")
                
            except Exception as e:
                print(f"   ❌ Virhe: {e}")
                failed += 1
                self.session.rollback()
                continue
        
        # Yhteenveto
        print(f"\n{'='*60}")
        print(f"📊 YHTEENVETO: {source.upper()}")
        print(f"{'='*60}")
        print(f"✅ Importoitu:  {imported}")
        print(f"⏭️  Ohitettu:    {skipped} (jo tietokannassa)")
        print(f"❌ Epäonnistui: {failed}")
        print(f"{'='*60}\n")
        
        return imported
    
    def import_all_sources(self, limit_per_source: int = 5) -> Dict[str, int]:
        """
        Importoi kaikista lähteistä.
        
        Args:
            limit_per_source: Montako arvostelua per lähde max
            
        Returns:
            Dictionary: {source: imported_count}
        """
        sources = ['hs', 'ts', 'il', 'ksml', 'sk']
        results = {}
        
        print("\n" + "="*60)
        print("🚀 MASS IMPORT - KAIKKI LÄHTEET")
        print("="*60 + "\n")
        
        for source in sources:
            try:
                imported = self.import_discovered_reviews(source, limit_per_source)
                results[source] = imported
            except Exception as e:
                print(f"❌ Virhe lähteessä {source}: {e}")
                results[source] = 0
        
        # Lopullinen yhteenveto
        total = sum(results.values())
        print("\n" + "="*60)
        print("🎉 VALMIS - LOPULLINEN YHTEENVETO")
        print("="*60)
        for source, count in results.items():
            print(f"{source.upper():6} : {count:2} arvostelua")
        print("-"*60)
        print(f"TOTAL  : {total:2} arvostelua")
        print("="*60 + "\n")
        
        # Tietokanta-tilastot
        print("📊 Tietokannan koko:")
        print(f"   Elokuvat:   {self.session.query(Movie).count()}")
        print(f"   Kriitikot:  {self.session.query(Critic).count()}")
        print(f"   Arvostelut: {self.session.query(Review).count()}")
        print()
        
        return results


# CLI-käyttö
if __name__ == '__main__':
    import sys
    
    importer = DiscoveryImporter()
    
    if len(sys.argv) > 1:
        source = sys.argv[1].lower()
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        if source == 'all':
            importer.import_all_sources(limit_per_source=limit)
        else:
            importer.import_discovered_reviews(source, limit)
    else:
        # Default: importoi kaikista lähteistä 3 arvostelua
        importer.import_all_sources(limit_per_source=3)
