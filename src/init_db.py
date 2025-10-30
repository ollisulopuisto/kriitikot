"""
Alustaa tietokannan ja importoi testidatan.
"""

import sys
sys.path.insert(0, '/workspaces/kriitikot/src')

from models import init_db, get_session, seed_publications, Movie, Critic, Publication, Review as DBReview
from scraper import HSScraper, KSMLScraper, ILScraper, TSScraper, SKScraper
import os
import re


def normalize_movie_title(title: str) -> str:
    """
    Poimii elokuvan nimen artikkeliotsikosta.
    """
    # Poista soft hyphens
    title = title.replace('\xad', '').replace('­', '')
    
    # Jos otsikko sisältää "-elokuva" tai " elokuva", poimii elokuvan nimen
    patterns = [
        r'([A-ZÄÖÅ][a-zäöå]+(?:\s+[a-zäöå]+){0,5})\s+-elokuv',
        r'([A-ZÄÖÅ][a-zäöå]+(?:\s+[a-zäöå]+){0,5})\s+elokuv',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            title = match.group(1).strip()
            break
    
    # Poista sijaintimaininnat ja jatko-osan merkinnät
    title = re.sub(r'\s+(Lapissa|Helsingissä|Turussa|jatko-osa|jakso \d+|osa \d+).*$', '', title, flags=re.IGNORECASE)
    
    return title.strip()


def get_or_create_movie(session, title: str):
    """Hakee tai luo elokuvan."""
    normalized = normalize_movie_title(title)
    movie = session.query(Movie).filter_by(title=normalized).first()
    if not movie:
        movie = Movie(title=normalized)
        session.add(movie)
        session.flush()
    return movie


def get_or_create_critic(session, name: str, media: str = None):
    """Hakee tai luo kriitikon."""
    critic = session.query(Critic).filter_by(name=name).first()
    if not critic:
        critic = Critic(name=name, media=media)
        session.add(critic)
        session.flush()
    elif media and not critic.media:
        # Päivitä media jos puuttuu
        critic.media = media
        session.flush()
    return critic


def get_publication(session, short_name: str):
    """Hakee julkaisun."""
    return session.query(Publication).filter_by(short_name=short_name).first()


def import_test_data(session):
    """Importoi testidatat tietokantaan."""
    test_data_dir = '/workspaces/kriitikot/tests/test_data'
    
    scrapers = [
        (HSScraper(), 'hs_review_1.html', 'hs'),
        (KSMLScraper(), 'ksml_review_1.html', 'ksml'),
        (ILScraper(), 'il_review_1.html', 'il'),
        (TSScraper(), 'ts_review_1.html', 'ts'),
        (SKScraper(), 'sk_review_1.html', 'sk'),
    ]
    
    imported = 0
    
    for scraper, filename, pub_short_name in scrapers:
        filepath = os.path.join(test_data_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue
        
        # Scrape review
        review = scraper.parse_file(filepath)
        if not review:
            print(f"⚠️  Failed to parse: {filename}")
            continue
        
        # Tarkista onko jo tietokannassa (URL on unique)
        existing = session.query(DBReview).filter_by(source_url=review.source_url).first()
        if existing:
            print(f"⏭️  Already exists: {review.movie_title} ({pub_short_name})")
            continue
        
        # Hae tai luo relaatiot
        movie = get_or_create_movie(session, review.movie_title)
        critic = get_or_create_critic(session, review.critic_name, media=pub_short_name.upper())
        publication = get_publication(session, pub_short_name)
        
        # Luo arvostelu
        # Jos source_url puuttuu, luo dummy URL
        source_url = review.source_url if review.source_url else f"https://example.com/{pub_short_name}/{filename}"
        
        db_review = DBReview(
            movie=movie,
            critic=critic,
            publication=publication,
            rating_stars=review.rating_stars,
            review_text=review.review_text,
            source_url=source_url
        )
        
        session.add(db_review)
        imported += 1
        
        print(f"✅ Imported: {movie.title} - {critic.name} ({publication.name}) - {review.rating_stars}★")
    
    session.commit()
    print(f"\n🎉 Successfully imported {imported} reviews!")
    
    # Näytä tilastot
    print("\n📊 Database stats:")
    print(f"   Movies: {session.query(Movie).count()}")
    print(f"   Critics: {session.query(Critic).count()}")
    print(f"   Publications: {session.query(Publication).count()}")
    print(f"   Reviews: {session.query(DBReview).count()}")


if __name__ == '__main__':
    print("🔧 Initializing database...")
    engine = init_db()
    session = get_session(engine)
    
    print("📰 Seeding publications...")
    seed_publications(session)
    
    print("\n📥 Importing test data...")
    import_test_data(session)
    
    print("\n✨ Done!")
