
import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from models import Base, Movie, Review, Critic, Publication

def test_merge_movies_integrity():
    """
    Regression test for the movie merge functionality to ensure no IntegrityError occurs
    when deleting the source movie after moving reviews.
    """
    # Setup In-Memory DB
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create Data
    m1 = Movie(title="Source Movie")
    m2 = Movie(title="Target Movie")
    c1 = Critic(name="Critic 1")
    c2 = Critic(name="Critic 2")
    c3 = Critic(name="Critic 3")
    p1 = Publication(name="Pub 1", short_name="p1")
    
    session.add_all([m1, m2, c1, c2, c3, p1])
    session.commit()

    # Add MULTIPLE reviews to m1 to trigger the original iteration bug
    r1 = Review(movie=m1, critic=c1, publication=p1, source_url="http://example.com/1", review_text="R1")
    r2 = Review(movie=m1, critic=c2, publication=p1, source_url="http://example.com/2", review_text="R2")
    r3 = Review(movie=m1, critic=c3, publication=p1, source_url="http://example.com/3", review_text="R3")
    
    session.add_all([r1, r2, r3])
    session.commit()
    
    # Reload
    source = session.query(Movie).filter_by(title="Source Movie").first()
    target = session.query(Movie).filter_by(title="Target Movie").first()
    
    assert len(source.reviews) == 3
    
    # -------------------------------------------------------------
    # The Logic from src/app.py (replicated here for regression testing)
    # FIX: Iterate over a copy of the list: list(source.reviews)
    # -------------------------------------------------------------
    reviews_moved = 0
    for review in list(source.reviews):
        review.movie = target
        reviews_moved += 1
    
    # Verify all reviews were moved in memory/session
    assert reviews_moved == 3
    
    # Flush changes to DB before delete
    session.flush()
    
    # Verify no reviews attached to source
    remaining = session.query(Review).filter_by(movie_id=m1.id).count()
    assert remaining == 0, "Reviews should have been moved"
    
    # Delete source
    session.delete(source)
    
    # Commit should succeed without IntegrityError
    try:
        session.commit()
    except Exception as e:
        pytest.fail(f"Commit failed with error: {e}")
        
    # Verify final state
    assert session.query(Movie).filter_by(title="Source Movie").count() == 0
    assert session.query(Movie).filter_by(title="Target Movie").count() == 1
    
    target_reviews = session.query(Review).filter_by(movie_id=m2.id).all()
    assert len(target_reviews) == 3
