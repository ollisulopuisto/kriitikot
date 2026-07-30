"""
SQLAlchemy tietokantamallit.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from contextlib import contextmanager
from datetime import datetime, timezone
import os

Base = declarative_base()


def utcnow():
    """Naiivi UTC-aika (kanta tallentaa naiiveja aikaleimoja)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Movie(Base):
    """Elokuva - normalisoitu nimi jota voi muokata admin-sivulta."""
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Elokuvan metatiedot
    published_date = Column(DateTime, nullable=True)  # Elokuvan julkaisupäivä (teattereissa)
    tmdb_id = Column(Integer, nullable=True)  # The Movie Database ID
    imdb_id = Column(String(20), nullable=True)  # IMDB ID (esim. "tt1234567")
    poster_url = Column(String(500), nullable=True)  # Julistekuva (TMDB)
    letterboxd_url = Column(String(500), nullable=True)  # Letterboxd-linkki
    nytleffaan_url = Column(String(500), nullable=True)  # Nytleffaan.fi-linkki
    
    # Relatio arvosteluihin
    reviews = relationship("Review", back_populates="movie")
    
    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}')>"


class Critic(Base):
    """Kriitikko - voi kirjoittaa useisiin julkaisuihin."""
    __tablename__ = 'critics'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    # POISTETTU: media kenttä (kriitikko voi kirjoittaa moneen mediaan)
    # Media-tieto tulee nyt Review-taulun kautta publication_id:stä
    created_at = Column(DateTime, default=utcnow)
    
    # Relatio arvosteluihin
    reviews = relationship("Review", back_populates="critic")
    
    def __repr__(self):
        return f"<Critic(id={self.id}, name='{self.name}')>"


class Publication(Base):
    """Julkaisu (HS, KSML, IL, TS, SK)."""
    __tablename__ = 'publications'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    short_name = Column(String(20), unique=True, nullable=False)  # 'hs', 'ksml', jne.
    created_at = Column(DateTime, default=utcnow)
    
    # Relatio arvosteluihin
    reviews = relationship("Review", back_populates="publication")
    
    def __repr__(self):
        return f"<Publication(id={self.id}, name='{self.name}')>"


class Review(Base):
    """Yksittäinen arvostelu."""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    
    # Foreign keys
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False, index=True)
    critic_id = Column(Integer, ForeignKey('critics.id'), nullable=False, index=True)
    publication_id = Column(Integer, ForeignKey('publications.id'), nullable=False, index=True)
    
    # Arvostelu
    rating_stars = Column(Integer, nullable=True)  # 1-5 tai None
    review_text = Column(Text, nullable=True)
    source_url = Column(String(500), unique=True, nullable=False)  # Unique - ei duplikaatteja
    
    # Julkaisustatus
    is_published = Column(Integer, default=0, nullable=False)  # 0 = pending, 1 = julkaistu (SQLite ei tue Boolean)
    
    # Metadata
    published_date = Column(DateTime, nullable=True)  # Arvion julkaisupäivä
    scraped_at = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)
    
    # Relatiot
    movie = relationship("Movie", back_populates="reviews")
    critic = relationship("Critic", back_populates="reviews")
    publication = relationship("Publication", back_populates="reviews")
    
    # Unique constraint: sama kriitikko voi arvostella saman elokuvan vain kerran (kaikkien julkaisujen yli)
    __table_args__ = (
        UniqueConstraint('movie_id', 'critic_id', name='_movie_critic_uc'),
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, movie='{self.movie.title if self.movie else None}', critic='{self.critic.name if self.critic else None}', stars={self.rating_stars})>"
    
    def to_dict(self):
        """Palauttaa sanakirjan (yhteensopiva vanhan Review-luokan kanssa)."""
        return {
            'id': self.id,
            'movie_title': self.movie.title if self.movie else None,
            'critic_name': self.critic.name if self.critic else None,
            'source_publication': self.publication.name if self.publication else None,
            'rating_stars': self.rating_stars,
            'review_text': self.review_text,
            'source_url': self.source_url,
            'is_published': bool(self.is_published),
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None
        }


# Database setup
def get_engine(db_path='reviews.db'):
    """Luo tai palauttaa tietokantayhteys."""
    db_file = os.path.join(os.path.dirname(__file__), '..', db_path)
    engine = create_engine(f'sqlite:///{db_file}', echo=False)
    return engine


def init_db(db_path='reviews.db'):
    """Alustaa tietokannan (luo taulut)."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    """Palauttaa session."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@contextmanager
def session_scope(engine=None):
    """Session context manager: rollback poikkeuksessa, sulkeminen aina.

    Kutsuja vastaa committaamisesta, jotta lukuoperaatiot eivät aiheuta
    turhia kirjoituksia.
    """
    session = get_session(engine)
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_publications(session):
    """Lisää perusjulkaisut tietokantaan."""
    publications = [
        Publication(name='Helsingin Sanomat', short_name='hs'),
        Publication(name='Keskisuomalainen', short_name='ksml'),
        Publication(name='Iltalehti', short_name='il'),
        Publication(name='Turun Sanomat', short_name='ts'),
        Publication(name='Suomen Kuvalehti', short_name='sk'),
        Publication(name='Ilta-Sanomat', short_name='is'),
        Publication(name='Episodi', short_name='episodi'),
        Publication(name='Muropaketti', short_name='muropaketti'),
        Publication(name='Film-O-Holic', short_name='filmoholic'),
        Publication(name='Kulttuuritoimitus', short_name='kulttuuritoimitus'),
        Publication(name='Demokraatti', short_name='demokraatti'),
        Publication(name='Kaleva', short_name='kaleva'),
    ]
    
    for pub in publications:
        existing = session.query(Publication).filter_by(short_name=pub.short_name).first()
        if not existing:
            session.add(pub)
    
    session.commit()
