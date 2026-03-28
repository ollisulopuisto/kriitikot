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
