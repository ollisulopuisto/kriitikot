#!/usr/bin/env python3
"""
Tietokannan tilanne - Näyttää yhteenvedon tietokannasta.
"""

from models import get_session, get_engine, Movie, Critic, Review, Publication
from datetime import datetime
import sys


def print_database_status(detailed=False):
    """Tulostaa tietokannan tilanteen."""
    
    engine = get_engine()
    session = get_session(engine)
    
    print("\n" + "="*70)
    print("📊 KRIITIKOT - TIETOKANNAN TILANNE")
    print("="*70)
    print(f"⏰ Aika: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Yhteenveto
    movie_count = session.query(Movie).count()
    critic_count = session.query(Critic).count()
    review_count = session.query(Review).count()
    pub_count = session.query(Publication).count()
    
    print("📈 YHTEENVETO:")
    print(f"   Elokuvia:   {movie_count:4}")
    print(f"   Kriitikoita: {critic_count:4}")
    print(f"   Arvosteluja: {review_count:4}")
    print(f"   Julkaisuja:  {pub_count:4}")
    print()
    
    # Arvostelut julkaisuittain
    print("📰 ARVOSTELUT JULKAISUITTAIN:")
    for pub in session.query(Publication).all():
        count = session.query(Review).filter_by(publication_id=pub.id).count()
        bar = "█" * count
        print(f"   {pub.short_name.upper():6} : {count:3} {bar}")
    print()
    
    # Arvosanajakauma
    print("⭐ ARVOSANAJAKAUMA:")
    for stars in range(1, 6):
        count = session.query(Review).filter_by(rating_stars=stars).count()
        bar = "★" * count
        print(f"   {stars} tähteä: {count:3} {bar}")
    
    no_rating = session.query(Review).filter(Review.rating_stars.is_(None)).count()
    if no_rating > 0:
        print(f"   Ei arviota: {no_rating:3}")
    print()
    
    # Aktiivisimmat kriitikot
    print("✍️  AKTIIVISIMMAT KRIITIKOT (Top 5):")
    from sqlalchemy import func
    top_critics = (
        session.query(Critic, func.count(Review.id).label('review_count'))
        .join(Review)
        .group_by(Critic.id)
        .order_by(func.count(Review.id).desc())
        .limit(5)
        .all()
    )
    
    for critic, count in top_critics:
        print(f"   {critic.name[:30]:30} : {count:2} arvostelua")
    print()
    
    # Viimeisimmät arvostelut
    print("🎬 VIIMEISIMMÄT ARVOSTELUT:")
    reviews = session.query(Review).order_by(Review.id.desc()).limit(10).all()
    
    for i, r in enumerate(reviews, 1):
        stars = "⭐" * (r.rating_stars or 0) if r.rating_stars else "—"
        pub = r.publication.short_name.upper()
        movie = r.movie.title[:25].ljust(25)
        critic = r.critic.name[:20].ljust(20)
        print(f"   {i:2}. {movie} | {critic} | {stars:10} ({pub})")
    print()
    
    if detailed:
        # Yksityiskohtainen listaus kaikista elokuvista
        print("="*70)
        print("🎬 KAIKKI ELOKUVAT:")
        print("="*70)
        
        movies = session.query(Movie).order_by(Movie.title).all()
        for movie in movies:
            reviews = session.query(Review).filter_by(movie_id=movie.id).all()
            print(f"\n{movie.title}")
            print("-" * len(movie.title))
            
            for r in reviews:
                stars = "⭐" * (r.rating_stars or 0) if r.rating_stars else "—"
                print(f"  {r.critic.name} ({r.publication.short_name.upper()}): {stars}")
                if r.source_url:
                    print(f"  🔗 {r.source_url}")
        print()
    
    print("="*70)
    
    session.close()


if __name__ == '__main__':
    detailed = '--detailed' in sys.argv or '-d' in sys.argv
    print_database_status(detailed=detailed)
