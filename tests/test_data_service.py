import pytest
import json
import sys
import os
from datetime import datetime
from collections import OrderedDict
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.data_service import DataService

@pytest.fixture
def mock_engine():
    return MagicMock()

@pytest.fixture
def data_service(mock_engine):
    return DataService(mock_engine)

def test_get_grouped_reviews_logic():
    # Mock data
    mock_movie = MagicMock()
    mock_movie.title = "Movie A"
    
    mock_critic = MagicMock()
    mock_critic.name = "Critic 1"
    
    mock_pub = MagicMock()
    mock_pub.short_name = "HS"
    
    mock_review = MagicMock()
    mock_review.movie = mock_movie
    mock_review.critic = mock_critic
    mock_review.publication = mock_pub
    mock_review.rating_stars = 4
    mock_review.is_published = 1
    mock_review.published_date = datetime(2024, 1, 1)
    mock_review.scraped_at = datetime(2024, 1, 1)
    
    # Mock session
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.options.return_value.all.return_value = [mock_review]
    mock_session.query.return_value.all.return_value = [mock_critic]
    
    service = DataService(None)
    grouped, critics, total = service.get_grouped_reviews(mock_session)
    
    assert total == 1
    assert "Movie A" in grouped
    assert "Critic 1" in grouped["Movie A"]
    assert grouped["Movie A"]["Critic 1"][0] == mock_review
    assert critics[0].name == "Critic 1"

def test_get_reviews_json_structure(data_service):
    # This test verifies that get_reviews_json returns correctly formatted JSON
    # containing the expected structure for frontend consumption via /reviews.json
    # using the optimized column-querying path.
    mock_row = (
        'Movie A',                      # Movie.title
        'Critic 1',                     # Critic.name
        42,                             # DBReview.id
        'Helsingin Sanomat',            # Publication.name
        'hs',                           # Publication.short_name
        5,                              # DBReview.rating_stars
        'Loistava elokuva',             # DBReview.review_text
        'https://example.com/review',   # DBReview.source_url
        1,                              # DBReview.is_published
        datetime(2024, 1, 1),           # DBReview.published_date
        datetime(2024, 1, 1, 12, 0)     # DBReview.scraped_at
    )

    with patch('services.data_service.get_session') as mock_sess_ctx:
        mock_session = mock_sess_ctx.return_value
        query_mock = mock_session.query.return_value
        query_mock.select_from.return_value.join.return_value.join.return_value.outerjoin.return_value.filter.return_value.all.return_value = [mock_row]

        reviews_json = data_service.get_reviews_json()
        all_reviews = json.loads(reviews_json)

        assert "Movie A" in all_reviews
        assert "Critic 1" in all_reviews["Movie A"]
        review = all_reviews["Movie A"]["Critic 1"][0]
        assert review['id'] == 42
        assert review['movie_title'] == 'Movie A'
        assert review['critic_name'] == 'Critic 1'
        assert review['source_publication'] == 'Helsingin Sanomat'
        assert review['publication_short'] == 'hs'
        assert review['rating_stars'] == 5
        assert review['review_text'] == 'Loistava elokuva'
        assert review['source_url'] == 'https://example.com/review'
        assert review['is_published'] is True
        assert review['published_date'] == '2024-01-01T00:00:00'
        assert review['scraped_at'] == '2024-01-01T12:00:00'


def test_get_index_data_does_not_serialize_redundant_reviews_json(data_service):
    mock_review = MagicMock()
    mock_review.rating_stars = 5
    mock_review.is_published = 1
    mock_review.published_date = datetime(2024, 1, 1)
    mock_review.critic_id = 1
    mock_review.publication.short_name = 'hs'

    with patch.object(DataService, 'get_grouped_reviews') as mock_grouped:
        mock_grouped.return_value = (
            OrderedDict({"Movie A": {"Critic 1": [mock_review]}}),
            [MagicMock(id=1, name="Critic 1")],
            1
        )

        with patch('services.data_service.get_session') as mock_sess_ctx:
            mock_session = mock_sess_ctx.return_value
            mock_session.query.return_value.filter.return_value.options.return_value.all.return_value = [mock_review]
            mock_session.query.return_value.all.return_value = []
            mock_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None

            data = data_service.get_index_data()

            # Ensure all_reviews_json was removed to save memory and serialization time
            assert 'all_reviews_json' not in data
            assert 'grouped_reviews' in data
            assert 'rating_distribution' in data
            assert 'pub_stats' in data
