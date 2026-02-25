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

def test_get_index_data_json_structure(data_service):
    # This test verifies that the JSON blob passed to the frontend is correctly formatted
    # and contains the expected keys for filters.js
    
    mock_review_dict = {
        'movie_title': 'Movie A',
        'critic_name': 'Critic 1',
        'rating_stars': 5,
        'source_publication': 'HS'
    }
    
    mock_review = MagicMock()
    mock_review.to_dict.return_value = mock_review_dict
    mock_review.is_published = 1
    mock_review.published_date = datetime(2024, 1, 1)
    
    # Setup the service to return predictable data
    with patch.object(DataService, 'get_grouped_reviews') as mock_grouped:
        mock_grouped.return_value = (
            OrderedDict({"Movie A": {"Critic 1": [mock_review]}}),
            [MagicMock(id=1, name="Critic 1")],
            1
        )
        
        with patch('services.data_service.get_session') as mock_sess_ctx:
            mock_session = mock_sess_ctx.return_value
            # Minimal mocks for other DB calls in get_index_data
            mock_session.query.return_value.filter.return_value.options.return_value.all.return_value = [mock_review]
            mock_session.query.return_value.all.return_value = [] # for movies, publications
            mock_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
            
            data = data_service.get_index_data()
            
            assert 'all_reviews_json' in data
            all_reviews = json.loads(data['all_reviews_json'])
            
            assert "Movie A" in all_reviews
            assert "Critic 1" in all_reviews["Movie A"]
            assert all_reviews["Movie A"]["Critic 1"][0]['rating_stars'] == 5
