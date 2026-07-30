"""Testit backfill_movie_metadata-apurille.

Tämä koodi ajetaan CI:ssä 6 tunnin välein (update_metadata.py), joten sen
käyttäytyminen kannattaa lukita testeillä. Verkkoa ei kutsuta: MetadataFetcher
korvataan tynkäobjektilla.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from metadata_fetcher import backfill_movie_metadata
from models import Movie


class StubFetcher:
    """Tynkä MetadataFetcher joka ei koske verkkoon."""

    def __init__(self, tmdb=None, poster_by_id=None, letterboxd=None, nytleffaan=None):
        self._tmdb = tmdb
        self._poster_by_id = poster_by_id
        self._letterboxd = letterboxd
        self._nytleffaan = nytleffaan
        self.calls = []

    def fetch_tmdb_data(self, title):
        self.calls.append('fetch_tmdb_data')
        return self._tmdb

    def get_poster_by_tmdb_id(self, tmdb_id):
        self.calls.append('get_poster_by_tmdb_id')
        return self._poster_by_id

    def search_movie_letterboxd(self, title):
        self.calls.append('search_movie_letterboxd')
        return self._letterboxd

    def search_movie_nytleffaan(self, title):
        self.calls.append('search_movie_nytleffaan')
        return self._nytleffaan


def test_fills_all_empty_fields():
    movie = Movie(title="Testielokuva")
    fetcher = StubFetcher(
        tmdb={'tmdb_id': 42, 'poster_url': 'http://img/p.jpg', 'imdb_id': 'tt42'},
        letterboxd='http://letterboxd/test',
        nytleffaan='http://nytleffaan/test',
    )

    updated = backfill_movie_metadata(movie, fetcher)

    assert movie.tmdb_id == 42
    assert movie.poster_url == 'http://img/p.jpg'
    assert movie.imdb_id == 'tt42'
    assert movie.letterboxd_url == 'http://letterboxd/test'
    assert movie.nytleffaan_url == 'http://nytleffaan/test'
    assert set(updated) == {'tmdb_id', 'poster_url', 'imdb_id',
                            'letterboxd_url', 'nytleffaan_url'}


def test_does_not_overwrite_existing_values():
    movie = Movie(title="Testielokuva", tmdb_id=1, poster_url='vanha.jpg',
                  imdb_id='tt1', letterboxd_url='vanha-lb', nytleffaan_url='vanha-nl')
    fetcher = StubFetcher(tmdb={'tmdb_id': 99, 'poster_url': 'uusi.jpg', 'imdb_id': 'tt99'},
                          letterboxd='uusi-lb', nytleffaan='uusi-nl')

    updated = backfill_movie_metadata(movie, fetcher)

    assert movie.tmdb_id == 1
    assert movie.poster_url == 'vanha.jpg'
    assert movie.letterboxd_url == 'vanha-lb'
    assert updated == []
    # Kaikki oli jo täytetty, joten TMDB-hakua ei tehdä lainkaan
    assert 'fetch_tmdb_data' not in fetcher.calls


def test_fetches_poster_by_id_when_tmdb_id_known():
    """Jos TMDB ID on jo tiedossa mutta juliste puuttuu, haetaan juliste ID:llä."""
    movie = Movie(title="Testielokuva", tmdb_id=7, letterboxd_url='x', nytleffaan_url='y')
    fetcher = StubFetcher(poster_by_id='http://img/by-id.jpg')

    updated = backfill_movie_metadata(movie, fetcher)

    assert movie.poster_url == 'http://img/by-id.jpg'
    assert updated == ['poster_url']
    assert 'get_poster_by_tmdb_id' in fetcher.calls
    assert 'fetch_tmdb_data' not in fetcher.calls


def test_handles_missing_tmdb_result():
    movie = Movie(title="Tuntematon")
    fetcher = StubFetcher(tmdb=None, letterboxd=None, nytleffaan=None)

    assert backfill_movie_metadata(movie, fetcher) == []
    assert movie.tmdb_id is None
    assert movie.poster_url is None


def test_partial_tmdb_result_only_fills_present_fields():
    """TMDB voi palauttaa tuloksen ilman julistetta tai IMDB-ID:tä."""
    movie = Movie(title="Testielokuva")
    fetcher = StubFetcher(tmdb={'tmdb_id': 5}, letterboxd=None, nytleffaan=None)

    updated = backfill_movie_metadata(movie, fetcher)

    assert movie.tmdb_id == 5
    assert movie.poster_url is None
    assert movie.imdb_id is None
    assert updated == ['tmdb_id']
