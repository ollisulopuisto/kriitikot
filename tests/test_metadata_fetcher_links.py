import sys
import os
from unittest.mock import patch

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
                raise Exception(f'HTTP {self.status_code}')
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
