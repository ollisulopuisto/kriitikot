#!/usr/bin/env python3
"""
Migraatioskripti: Kriitikko useissa medioissa.

Tämä skripti:
1. Luo uuden tietokannan uudella skeemalla
2. Migroi datan vanhasta tietokannasta uuteen
3. Poistaa Critic.media kentän (tieto tulee nyt Review.publication_id:stä)
"""

import sys
from pathlib import Path

# Lisää src/ polku pythonpathiin
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    get_session, init_db, seed_publications,
    Movie, Critic, Publication, Review as NewReview
)
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# VANHA skeema (ennen muutosta)
OldBase = declarative_base()


class OldCritic(OldBase):
    """Vanha Critic-malli jossa media-kenttä."""
    __tablename__ = 'critics'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    media = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    reviews = relationship("OldReview", back_populates="critic")


class OldMovie(OldBase):
    """Vanha Movie-malli."""
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    reviews = relationship("OldReview", back_populates="movie")


class OldPublication(OldBase):
    """Vanha Publication-malli."""
    __tablename__ = 'publications'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    short_name = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    reviews = relationship("OldReview", back_populates="publication")


class OldReview(OldBase):
    """Vanha Review-malli."""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    critic_id = Column(Integer, ForeignKey('critics.id'), nullable=False)
    publication_id = Column(Integer, ForeignKey('publications.id'), nullable=False)
    rating_stars = Column(Integer, nullable=True)
    review_text = Column(Text, nullable=True)
    source_url = Column(String(500), unique=True, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    movie = relationship("OldMovie", back_populates="reviews")
    critic = relationship("OldCritic", back_populates="reviews")
    publication = relationship("OldPublication", back_populates="reviews")


def migrate_database(old_db='reviews.db', new_db='reviews_new.db'):
    """Migroi tietokanta vanhasta uuteen skeemaan."""
    
    # Polut
    src_dir = Path(__file__).parent
    old_db_path = src_dir.parent / old_db
    new_db_path = src_dir.parent / new_db
    
    print("🔍 Tarkistetaan vanhan tietokannan olemassaolo...")
    if not old_db_path.exists():
        print(f"❌ Vanhaa tietokantaa ei löydy: {old_db_path}")
        print("   Luodaan uusi tyhjä tietokanta...")
        new_engine = init_db(new_db)
        new_session = get_session(new_engine)
        seed_publications(new_session)
        new_session.close()
        print(f"✅ Uusi tietokanta luotu: {new_db_path}")
        return
    
    print(f"✅ Vanha tietokanta löytyi: {old_db_path}")
    
    # Luo yhteys vanhaan tietokantaan
    old_engine = create_engine(f'sqlite:///{old_db_path}', echo=False)
    OldSession = sessionmaker(bind=old_engine)
    old_session = OldSession()
    
    # Luo uusi tietokanta
    print("\n📝 Luodaan uusi tietokanta uudella skeemalla...")
    new_engine = init_db(new_db)
    new_session = get_session(new_engine)
    
    # Seed julkaisut
    seed_publications(new_session)
    
    try:
        # Hae kaikki vanhat publikaatiot (id-mappaus)
        print("\n🔄 Migroidaan julkaisut...")
        old_pubs = old_session.query(OldPublication).all()
        pub_id_map = {}
        
        for old_pub in old_pubs:
            new_pub = new_session.query(Publication).filter_by(
                short_name=old_pub.short_name
            ).first()
            if new_pub:
                pub_id_map[old_pub.id] = new_pub.id
                print(f"   ✓ {old_pub.name} (ID: {old_pub.id} → {new_pub.id})")
        
        # Hae kaikki vanhat elokuvat
        print("\n🔄 Migroidaan elokuvat...")
        old_movies = old_session.query(OldMovie).all()
        movie_id_map = {}
        
        for old_movie in old_movies:
            new_movie = Movie(
                title=old_movie.title,
                created_at=old_movie.created_at,
                updated_at=old_movie.updated_at
            )
            new_session.add(new_movie)
            new_session.flush()
            movie_id_map[old_movie.id] = new_movie.id
            print(f"   ✓ {old_movie.title} (ID: {old_movie.id} → {new_movie.id})")
        
        # Hae kaikki vanhat kriitikot (ILMAN media-kenttää)
        print("\n🔄 Migroidaan kriitikot (ILMAN media-kenttää)...")
        old_critics = old_session.query(OldCritic).all()
        critic_id_map = {}
        
        for old_critic in old_critics:
            new_critic = Critic(
                name=old_critic.name,
                created_at=old_critic.created_at
                # POISTETTU: media kenttä
            )
            new_session.add(new_critic)
            new_session.flush()
            critic_id_map[old_critic.id] = new_critic.id
            media_info = f" [{old_critic.media}]" if old_critic.media else ""
            print(f"   ✓ {old_critic.name}{media_info} (ID: {old_critic.id} → {new_critic.id})")
        
        # Hae kaikki vanhat arvostelut
        print("\n🔄 Migroidaan arvostelut...")
        old_reviews = old_session.query(OldReview).all()
        
        for old_review in old_reviews:
            new_review = NewReview(
                movie_id=movie_id_map[old_review.movie_id],
                critic_id=critic_id_map[old_review.critic_id],
                publication_id=pub_id_map[old_review.publication_id],
                rating_stars=old_review.rating_stars,
                review_text=old_review.review_text,
                source_url=old_review.source_url,
                scraped_at=old_review.scraped_at,
                created_at=old_review.created_at
            )
            new_session.add(new_review)
            
            movie_title = old_review.movie.title if old_review.movie else '?'
            critic_name = old_review.critic.name if old_review.critic else '?'
            pub_name = old_review.publication.short_name if old_review.publication else '?'
            stars = f"{old_review.rating_stars}★" if old_review.rating_stars else "–"
            print(f"   ✓ {movie_title} / {critic_name} / {pub_name.upper()} / {stars}")
        
        new_session.commit()
        
        print("\n✅ Migraatio onnistui!")
        print(f"   - Elokuvat: {len(old_movies)}")
        print(f"   - Kriitikot: {len(old_critics)}")
        print(f"   - Julkaisut: {len(old_pubs)}")
        print(f"   - Arvostelut: {len(old_reviews)}")
        print(f"\n📌 Uusi tietokanta: {new_db_path}")
        print("\n⚠️  SEURAAVAT VAIHEET:")
        print("   1. Testaa uusi tietokanta: python3 src/app.py")
        print("   2. Jos toimii, korvaa vanha:")
        print(f"      mv {old_db_path} {old_db_path}.backup")
        print(f"      mv {new_db_path} {old_db_path}")
        
    except Exception as e:
        print(f"\n❌ Virhe migraatiossa: {e}")
        new_session.rollback()
        raise
    
    finally:
        old_session.close()
        new_session.close()


if __name__ == '__main__':
    migrate_database()
