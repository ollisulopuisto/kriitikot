
import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from models import Base, Movie, Review, Critic, Publication
from services.merge_service import merge_movies


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def test_merge_moves_all_reviews(session):
    """Kaikki arvostelut siirtyvät eikä duplikaatin poisto kaada IntegrityErroriin."""
    source = Movie(title="Source Movie")
    target = Movie(title="Target Movie")
    critics = [Critic(name=f"Critic {i}") for i in range(1, 4)]
    pub = Publication(name="Pub 1", short_name="p1")

    session.add_all([source, target, pub, *critics])
    session.commit()

    for i, critic in enumerate(critics, 1):
        session.add(Review(movie=source, critic=critic, publication=pub,
                           source_url=f"http://example.com/{i}"))
    session.commit()

    result = merge_movies(session, canonical_id=target.id, duplicate_id=source.id)
    session.commit()

    assert result.moved == 3
    assert result.dropped == 0
    assert session.query(Movie).filter_by(title="Source Movie").count() == 0
    assert session.query(Review).filter_by(movie_id=target.id).count() == 3


def test_merge_drops_reviews_that_would_collide(session):
    """Sama kriitikko molemmilla elokuvilla: duplikaatin arvostelu poistetaan.

    Ilman tätä UniqueConstraint('movie_id', 'critic_id') kaataisi yhdistämisen.
    """
    source = Movie(title="Elokuva (2026)")
    target = Movie(title="Elokuva")
    shared = Critic(name="Sama Kriitikko")
    other = Critic(name="Toinen Kriitikko")
    pub = Publication(name="Pub 1", short_name="p1")

    session.add_all([source, target, shared, other, pub])
    session.commit()

    # shared arvostelee molemmat elokuvat -> törmäys
    session.add(Review(movie=target, critic=shared, publication=pub,
                       source_url="http://example.com/canonical"))
    session.add(Review(movie=source, critic=shared, publication=pub,
                       source_url="http://example.com/duplicate"))
    session.add(Review(movie=source, critic=other, publication=pub,
                       source_url="http://example.com/other"))
    session.commit()

    result = merge_movies(session, canonical_id=target.id, duplicate_id=source.id)
    session.commit()  # ei saa kaatua

    assert result.moved == 1      # vain 'other' siirtyi
    assert result.dropped == 1    # 'shared' pudotettiin
    assert session.query(Movie).filter_by(title="Elokuva (2026)").count() == 0

    remaining = session.query(Review).filter_by(movie_id=target.id).all()
    assert len(remaining) == 2
    # Kanonisen alkuperäinen arvostelu säilyy, duplikaatin versio katoaa
    assert {r.source_url for r in remaining} == {
        "http://example.com/canonical",
        "http://example.com/other",
    }


def test_merge_carries_metadata_to_canonical(session):
    """Duplikaatin metatiedot siirtyvät kanoniselle jos ne puuttuvat sieltä."""
    source = Movie(title="Source", tmdb_id=123, poster_url="http://img/poster.jpg",
                   letterboxd_url="http://letterboxd/x")
    target = Movie(title="Target", imdb_id="tt999")

    session.add_all([source, target])
    session.commit()

    result = merge_movies(session, canonical_id=target.id, duplicate_id=source.id)
    session.commit()

    assert target.tmdb_id == 123
    assert target.poster_url == "http://img/poster.jpg"
    assert target.letterboxd_url == "http://letterboxd/x"
    assert target.imdb_id == "tt999"  # omaa arvoa ei ylikirjoiteta
    assert set(result.carried_metadata) == {'tmdb_id', 'poster_url', 'letterboxd_url'}


def test_merge_does_not_overwrite_existing_metadata(session):
    """Kanonisen omat metatiedot voittavat duplikaatin vastaavat."""
    source = Movie(title="Source", tmdb_id=111, poster_url="http://img/dup.jpg")
    target = Movie(title="Target", tmdb_id=222, poster_url="http://img/canon.jpg")

    session.add_all([source, target])
    session.commit()

    result = merge_movies(session, canonical_id=target.id, duplicate_id=source.id)
    session.commit()

    assert target.tmdb_id == 222
    assert target.poster_url == "http://img/canon.jpg"
    assert result.carried_metadata == []


def test_merge_returns_none_for_missing_movie(session):
    """Puuttuva elokuva palauttaa Nonen eikä kaadu."""
    movie = Movie(title="Only Movie")
    session.add(movie)
    session.commit()

    assert merge_movies(session, canonical_id=movie.id, duplicate_id=9999) is None
    assert merge_movies(session, canonical_id=9999, duplicate_id=movie.id) is None
