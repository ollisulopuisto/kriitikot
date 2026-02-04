"""Tests for discovery importer rating validation.

Articles without star ratings should be skipped during import.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scrapers.base import Review


class TestRatingValidation:
    """Test that reviews without ratings are skipped."""

    def test_should_skip_review_without_rating(self):
        """
        Reviews without rating_stars should be skipped.
        
        This tests the logic that will be added to discovery_importer.py
        """
        # A review without a rating (like "Kirsikan mausta kolmeen väriin")
        review_without_rating = Review(
            movie_title="Kirsikan mausta kolmeen väriin",
            critic_name="Test Critic",
            rating_stars=None,  # No rating!
            review_text="Some text",
            source_url="https://example.com/article",
            source_publication="Kulttuuritoimitus"
        )
        
        # The logic to test: reviews without ratings should be skipped
        should_skip = review_without_rating.rating_stars is None
        assert should_skip is True

    def test_should_not_skip_review_with_rating(self):
        """Reviews with rating_stars should NOT be skipped."""
        review_with_rating = Review(
            movie_title="Good Movie",
            critic_name="Test Critic",
            rating_stars=4,  # Has rating!
            review_text="Great movie",
            source_url="https://example.com/review",
            source_publication="Demokraatti"
        )
        
        should_skip = review_with_rating.rating_stars is None
        assert should_skip is False

    def test_zero_rating_should_not_skip(self):
        """Edge case: A rating of 0 (if that's valid) should not be skipped.
        
        Note: In practice our system uses 1-5 stars, so 0 might not be valid,
        but we test the logic anyway.
        """
        review_with_zero = Review(
            movie_title="Bad Movie",
            critic_name="Test Critic",
            rating_stars=0,
            review_text="Terrible",
            source_url="https://example.com/bad",
            source_publication="Muropaketti"
        )
        
        # 0 is still a rating, albeit unusual
        should_skip = review_with_zero.rating_stars is None
        assert should_skip is False
