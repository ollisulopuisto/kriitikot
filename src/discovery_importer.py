"""
Discovery Importer - Yhdistää discovery-moduulin ja tietokannan.

Hakee uusia arvosteluja discovery-moduulilla ja tallentaa ne tietokantaan.
"""

from discovery import MetaScraper
from models import get_session, get_engine, Movie, Critic, Publication, Review
from scrapers import scrapers as SCRAPERS
from movie_normalizer import get_canonical_title
from metadata_fetcher import MetadataFetcher, backfill_movie_metadata
from typing import Dict
import re
import requests


class DiscoveryImporter:
    """
    Yhdistää discovery-moduulin ja tietokannan.
    
    1. Löytää uudet arvostelut discovery-moduulilla
    2. Scrapaa arvostelut oikeilla scrapereilla
    3. Tallentaa tietokantaan (välttää duplikaatit)
    """
    
    def __init__(self):
        self.source_failures = {}
        from pathlib import Path
        self.is_cache_path = Path(__file__).resolve().parents[1] / 'data' / 'is-discovery.json'
        self.meta_scraper = MetaScraper()
        self.engine = get_engine()
        self.session = get_session(self.engine)
        self.metadata_fetcher = MetadataFetcher()
        
        # Scrapers per source — sama rekisteri kuin scrapers/__init__.py:ssä
        self.scrapers = SCRAPERS
    
    def resolve_hs_preview_title(self, asset: dict, source_url: str = None):
        """Match an existing film in two independent preview fields, never an h1.

        Reject overlapping DB titles and sequel continuations rather than choosing
        a short title or fuzzy match. Unresolved previews remain source failures.
        """
        if asset.get('storyLogo') != 'Elokuva-arvio':
            return None
        import unicodedata

        def normalize(text):
            text = unicodedata.normalize('NFKC', str(text or '')).casefold()
            text = re.sub(r'[\u00ad\u200b\u200c\u200d\u2060\ufeff]', '', text)
            return re.sub(r'[^\w]+', ' ', text).strip()

        picture = asset.get('mainPicture') or {}
        fields = [asset.get('metaTitle'), asset.get('ingress'),
                  picture.get('caption') if isinstance(picture, dict) else None]
        normalized = [normalize(text) for text in fields]
        candidates = []
        for movie in self.session.query(Movie).all():
            title = normalize(movie.title)
            if not title:
                continue
            pattern = r'(?<!\w)' + re.escape(title) + r'(?!\w)'
            hits = [i for i, text in enumerate(normalized) if re.search(pattern, text)]
            if len(hits) < 2:
                continue
            # A known original must not absorb an unknown numbered/subtitled sequel.
            raw_pattern = r'(?<!\w)' + r'[\W_]+'.join(re.escape(t) for t in title.split()) + r'(?!\w)\s*(?::|[-–—](?!(?:elokuva|dokumentti|draama|komedia|trilleri|animaatio)\w*\b)|[0-9]|[IVX]+\b)'
            if any(re.search(raw_pattern, unicodedata.normalize('NFKC', str(fields[i])), re.IGNORECASE) for i in hits):
                continue
            candidates.append(movie.title)
        return candidates[0] if len(candidates) == 1 else None

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
        
        # Poista sulut ja niiden sisältö (esim. englantilainen nimi)
        # Mutta vain jos ne eivät ole koko nimi
        clean_title = re.sub(r'\(.*?\)', '', title).strip()
        if clean_title:
            title = clean_title
        
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
            
            # Hae metatiedot uudelle elokuvalle
            print(f"   🎬 Luotiin uusi elokuva: {canonical_title}")
            try:
                added = backfill_movie_metadata(movie, self.metadata_fetcher)
                self.session.commit()
                print(f"   📊 Metatiedot haettu: {', '.join(added) if added else 'ei löytynyt'}")

            except Exception as e:
                print(f"   ⚠️  Metatietojen haku epäonnistui: {e}")
                # Jatka normaalisti vaikka metadata haku epäonnistuu
        elif canonical_title != normalized:
            # Löytyi vastaava, käytetään olemassa olevaa
            print(f"   🔗 Yhdistetty olemassa olevaan: {canonical_title}")
        return movie
    
    def get_or_create_critic(self, name: str, media: str = None) -> Critic:
        """Hakee tai luo kriitikon.
        
        HUOM: media-parametri ei enää käytössä (poistettu Critic-mallista).
        Media-tieto tulee nyt Review.publication_id:stä.
        """
        critic = self.session.query(Critic).filter_by(name=name).first()
        if not critic:
            critic = Critic(name=name)  # EI ENÄÄ media-kenttää
            self.session.add(critic)
            self.session.flush()
            print(f"   ✍️  Luotiin uusi kriitikko: {name}")
        return critic
    
    def get_publication(self, short_name: str) -> Publication:
        """Hakee julkaisun."""
        return self.session.query(Publication).filter_by(short_name=short_name).first()
    
    def import_discovered_reviews(self, source: str, limit: int = 20, request_budget: int = 40) -> int:
        """
        Löytää ja importoi uudet arvostelut lähteestä.
        
        Args:
            source: Lähteen tunniste ('hs', 'ksml', 'il', 'ts', 'sk', 'is', 'episodi')
            limit: Montako max arvostelua etsitään
            
        Returns:
            Importoitujen arvostelujen määrä
        """
        print(f"\n{'='*60}")
        print(f"🔍 IMPORT: {source.upper()}")
        print(f"{'='*60}\n")
        
        self.source_failures[source] = 0
        if not hasattr(self, 'source_exclusions'):
            self.source_exclusions = {}
        exclusions = {}
        self.source_exclusions[source] = exclusions

        # 1. Löydä uudet arvostelut
        try:
            discovered = self.meta_scraper.discover_new_reviews(source, limit)
        except Exception as exc:
            self.source_failures[source] = 1
            print(f'Discovery failed for {source}: {exc}')
            return 0
        print(f"✅ Löydettiin {len(discovered)} arvostelua\n")
        
        if not discovered:
            print("⚠️  Ei uusia arvosteluja\n")
            return 0
        
        queue = None
        stats = {'discovered':len(discovered), 'requested':0, 'admitted':0,
                 'excluded':0, 'failed':0, 'queued':0}
        if source == 'is':
            from is_discovery_queue import ISDiscoveryQueue
            queue = ISDiscoveryQueue(self.session, path=getattr(self, 'is_cache_path', None))
            queue.enqueue(discovered)
            discovered = queue.due(min(40,max(0,request_budget)))
            self.is_stats = stats

        # 2. Scrape ja tallenna
        scraper = self.scrapers.get(source)
        if not scraper:
            print(f"❌ Ei scraperia lähteelle: {source}")
            self.source_failures[source] = 1
            return 0
        
        publication = self.get_publication(source)
        if not publication:
            print(f"❌ Julkaisua ei löydy tietokannasta: {source}")
            self.source_failures[source] = 1
            return 0
        
        imported = 0
        skipped = 0
        failed = 0
        
        for i, discovery in enumerate(discovered, 1):
            if queue and stats['admitted'] >= max(0,limit):
                break
            url = discovery['url']
            title_preview = discovery['title'][:60]
            
            print(f"\n[{i}/{len(discovered)}] {title_preview}...")
            print(f"   🔗 {url}")
            
            # Tarkista onko jo tietokannassa samalta kriitikolta sama elokuva
            # Huom: movie-objekti ja critic-objekti luodaan tai haetaan vasta myöhemmin.
            # Joudumme tekemään tämän tarkistuksen hieman myöhemmin importointiprosessissa.
            # Tässä vaiheessa tarkistetaan vain URL.
            existing_by_url = self.session.query(Review).filter_by(source_url=url).first()
            if existing_by_url:
                print("   ⏭️  Jo tietokannassa (URL-duplikaatti)")
                skipped += 1
                if queue:
                    queue.finish(url, 'imported')
                continue
            
            # Scrape arvostelu
            try:
                # Lataa HTML ja parsea
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                if queue:
                    if stats['requested']:
                        import time
                        time.sleep(1)
                    stats['requested'] += 1
                response = requests.get(url, headers=headers, timeout=10, **({'allow_redirects':False} if queue else {}))
                response.raise_for_status()
                if queue and 300 <= response.status_code < 400:
                    raise ValueError('IS article redirect needs review')
                html = response.text

                if source == 'is':
                    reason = scraper.exclusion_reason(html)
                    if reason:
                        print(f"   ⏭️  IS exclusion: {reason}")
                        skipped += 1
                        if queue:
                            stats['excluded'] += 1
                            queue.finish(url, 'excluded')
                        continue

                if source in {'demokraatti', 'ksml'}:
                    reason = scraper.exclusion_reason(html)
                    if reason:
                        print(f'   ⏭️  {source.upper()} exclusion: {reason}')
                        exclusions[reason] = exclusions.get(reason, 0) + 1
                        skipped += 1
                        continue

                review = scraper.parse_html(html, url)
                if not review:
                    print("   ❌ Scraping epäonnistui")
                    failed += 1
                    if queue:
                        stats['failed'] += 1
                        queue.finish(url, 'failed')
                    continue

                # Discovery alone cannot prove an article is a complete review.
                # Missing metadata is unresolved, not evidence of a non-review.
                if source == 'hs' and review.rating_stars is None:
                    print('   ⏭️  HS review has no star rating; not imported')
                    skipped += 1
                    continue

                title = review.movie_title
                author = review.critic_name
                placeholders = {'unknown', 'tuntematon', source.casefold(), publication.name.casefold()}
                valid_title = isinstance(title,str) and bool(title.strip())
                valid_author = (isinstance(author,str) and bool(author.strip()) and
                                author.strip().casefold() not in placeholders and
                                not re.match(r'https?://',author.strip(),re.IGNORECASE))
                valid_rating = type(review.rating_stars) is int and 1 <= review.rating_stars <= 5
                if not (valid_title and valid_author and valid_rating):
                    print('   ❌ Incomplete review identity, author or rating; needs source review')
                    failed += 1
                    if queue:
                        stats['failed'] += 1
                        queue.finish(url, 'failed')
                    continue

                # If HS returned its article headline, the film facts were
                # absent from the public preview. Require repeated existing-film evidence.
                resolved_movie = None
                if source == 'hs' and not scraper._extract_movie_title(review.raw_data, allow_headline=False):
                    resolved = self.resolve_hs_preview_title(review.raw_data, url)
                    if not resolved:
                        print("   ❌ HS preview: film title needs manual review")
                        failed += 1
                        continue
                    resolved_movie = self.session.query(Movie).filter_by(title=resolved).one()
                    review.movie_title = resolved_movie.title

                if queue:
                    stats['admitted'] += 1

                # Luo relaatiot
                movie = resolved_movie if resolved_movie is not None else self.get_or_create_movie(review.movie_title)
                critic = self.get_or_create_critic(review.critic_name, media=source.upper())

                # Tarkista uusi duplikaatti: onko samalta kriitikolta jo arvostelu tälle elokuvalle?
                existing_by_critic_and_movie = self.session.query(Review).filter(
                    Review.movie_id == movie.id,
                    Review.critic_id == critic.id
                ).first()

                if existing_by_critic_and_movie:
                    print(f"   ⏭️  Ohitettu: Kriitikolla {critic.name} on jo arvostelu elokuvasta {movie.title}")
                    skipped += 1
                    self.session.rollback() # Varmuuden vuoksi, jos flush on tapahtunut
                    if queue:
                        stats['excluded'] += 1
                        queue.finish(url, 'excluded')
                    continue
                
                # Tallenna arvostelu (AUTOMAATTISESTI JULKAISTU - pending pois päältä)
                db_review = Review(
                    movie=movie,
                    critic=critic,
                    publication=publication,
                    rating_stars=review.rating_stars,
                    review_text=review.review_text,
                    source_url=review.source_url,
                    is_published=1  # AUTOMAATTISESTI JULKAISTU - muutettu 0:sta 1:ksi
                )
                
                self.session.add(db_review)
                self.session.commit()
                
                if queue:
                    queue.finish(url, 'imported')
                imported += 1
                print(f"   ✅ Tallennettu (julkaistu): {movie.title} - {critic.name} - {review.rating_stars}★")
                
            except Exception as e:
                print(f"   ❌ Virhe: {e}")
                failed += 1
                self.session.rollback()
                if queue:
                    stats['failed'] += 1
                    queue.finish(url, 'failed')
                continue
        
        if queue:
            stats['queued'] = queue.queued()
            print(f'IS discovery outcomes: {stats}')
        self.source_failures[source] = max(failed, queue.failed() if queue else 0)

        # Yhteenveto
        print(f"\n{'='*60}")
        print(f"📊 YHTEENVETO: {source.upper()}")
        print(f"{'='*60}")
        print(f"✅ Importoitu:  {imported}")
        print(f"⏭️  Ohitettu:    {skipped} (jo tietokannassa)")
        print(f"❌ Epäonnistui: {failed}")
        for reason, count in exclusions.items():
            print(f'ℹ️  Explicit exclusion {reason}: {count} (not imported)')
        print(f"{'='*60}\n")
        
        return imported
    
    def import_all_sources(self, limit_per_source: int = 10) -> Dict[str, int]:
        """
        Importoi kaikista lähteistä.
        
        Args:
            limit_per_source: Montako arvostelua per lähde max
            
        Returns:
            Dictionary: {source: imported_count}
        """
        sources = ['hs', 'ts', 'il', 'ksml', 'sk', 'is', 'episodi', 'muropaketti', 'filmoholic', 'kulttuuritoimitus', 'demokraatti']  # kaleva removed due to paywall
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
                self.source_failures[source] = max(1, self.source_failures.get(source, 0))
        
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
        # Default: importoi kaikista lähteistä 10 arvostelua
        importer.import_all_sources(limit_per_source=10)

    sys.exit(1 if any(importer.source_failures.values()) else 0)
