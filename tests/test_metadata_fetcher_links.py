import sys
import os
from unittest.mock import patch
import requests

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from metadata_fetcher import MetadataFetcher


def _response(status_code):
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = ''

        def raise_for_status(self):
            if self.status_code >= 400:
                error = requests.exceptions.HTTPError(f'HTTP {self.status_code}', response=self)
                raise error

        def json(self):
            return {}

    return MockResponse(status_code)


def test_letterboxd_accepts_redirect_status_for_direct_slug():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(301)) as mock_head:
        url = fetcher.search_movie_letterboxd('Inception', prefer_recent=False)

    assert url == 'https://letterboxd.com/film/inception/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_letterboxd_accepts_success_status_for_direct_slug():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(200)) as mock_head:
        url = fetcher.search_movie_letterboxd('Inception', prefer_recent=False)

    assert url == 'https://letterboxd.com/film/inception/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_nytleffaan_slug_transliteration_uses_lowercase_ascii():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(200)) as mock_head:
        url = fetcher.search_movie_nytleffaan('Ääliö Ööli Åke', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/aalioooliake/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_nytleffaan_slug_removes_punctuation_but_keeps_hyphens():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(200)) as mock_head:
        url = fetcher.search_movie_nytleffaan('Duudsonit-elokuva: Kotiinpaluu', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/duudsonit-elokuva-kotiinpaluu/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_nytleffaan_slug_normalizes_en_dash_separator():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(200)) as mock_head:
        url = fetcher.search_movie_nytleffaan('Duudsonit-elokuva – Kotiinpaluu', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/duudsonit-elokuva-kotiinpaluu/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_nytleffaan_slug_normalizes_em_dash_separator():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(200)) as mock_head:
        url = fetcher.search_movie_nytleffaan('Duudsonit-elokuva — Kotiinpaluu', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/duudsonit-elokuva-kotiinpaluu/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_nytleffaan_returns_direct_url_when_head_verification_fails():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', side_effect=requests.exceptions.ConnectionError('blocked')) as mock_head:
        url = fetcher.search_movie_nytleffaan('Sinners', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/sinners/'
    mock_head.assert_called_once()


def test_nytleffaan_returns_direct_url_when_head_times_out():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', side_effect=requests.exceptions.Timeout('timeout')) as mock_head:
        url = fetcher.search_movie_nytleffaan('Sinners', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/sinners/'
    mock_head.assert_called_once()


def test_nytleffaan_accepts_403_as_usable_bot_protection_response():
    fetcher = MetadataFetcher()

    with patch('metadata_fetcher.requests.head', return_value=_response(403)) as mock_head:
        url = fetcher.search_movie_nytleffaan('Sinners', prefer_recent=False)

    assert url == 'https://www.nytleffaan.fi/elokuva/sinners/'
    mock_head.assert_called_once()
    assert mock_head.call_args.kwargs.get('allow_redirects') is True


def test_tmdb_prefers_result_with_poster_when_recent_preference_enabled():
    fetcher = MetadataFetcher()

    results = [
        {'id': 1, 'title': 'Movie', 'release_date': '2026-01-01', 'poster_path': None},
        {'id': 2, 'title': 'Movie', 'release_date': '2025-12-01', 'poster_path': '/poster.jpg'},
    ]

    selected = fetcher._select_best_tmdb_result(results, prefer_recent=True)

    assert selected['id'] == 2


def test_tmdb_search_falls_back_to_english_language_when_fi_has_no_results():
    fetcher = MetadataFetcher()
    fetcher.tmdb_api_key = 'test-key'

    fi_response = _response(200)
    fi_response.json = lambda: {'results': []}

    en_response = _response(200)
    en_response.json = lambda: {
        'results': [
            {
                'id': 99,
                'title': 'Sinners',
                'original_title': 'Sinners',
                'release_date': '2025-04-18',
                'poster_path': '/abc.jpg',
                'overview': 'Test overview',
                'vote_average': 7.1
            }
        ]
    }

    with patch('metadata_fetcher.requests.get', side_effect=[fi_response, en_response]) as mock_get:
        result = fetcher.search_movie_tmdb('Sinners', prefer_recent=False)

    assert result is not None
    assert result['tmdb_id'] == 99
    assert result['poster_url'].endswith('/abc.jpg')
    assert mock_get.call_args_list[0].kwargs['params']['language'] == 'fi-FI'
    assert mock_get.call_args_list[1].kwargs['params']['language'] == 'en-US'


def test_tmdb_search_uses_no_language_fallback_after_fi_and_en():
    fetcher = MetadataFetcher()
    fetcher.tmdb_api_key = 'test-key'

    fi_response = _response(200)
    fi_response.json = lambda: {'results': []}

    en_response = _response(200)
    en_response.json = lambda: {'results': []}

    no_lang_response = _response(200)
    no_lang_response.json = lambda: {
        'results': [
            {
                'id': 101,
                'title': 'Fallback',
                'original_title': 'Fallback',
                'release_date': '2025-01-01',
                'poster_path': '/fallback.jpg',
                'overview': '',
                'vote_average': 6.0
            }
        ]
    }

    with patch('metadata_fetcher.requests.get', side_effect=[fi_response, en_response, no_lang_response]) as mock_get:
        result = fetcher.search_movie_tmdb('Fallback', prefer_recent=False)

    assert result is not None
    assert result['tmdb_id'] == 101
    params_fi = mock_get.call_args_list[0].kwargs['params']
    params_en = mock_get.call_args_list[1].kwargs['params']
    params_no_lang = mock_get.call_args_list[2].kwargs['params']
    assert params_fi['language'] == 'fi-FI'
    assert params_en['language'] == 'en-US'
    assert 'language' not in params_no_lang
