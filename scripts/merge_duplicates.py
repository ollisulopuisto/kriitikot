
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import get_session, get_engine, Movie, Review
from movie_normalizer import are_same_movie

def merge_movies(session, canonical_id, duplicate_id):
    """
    Merges movie with duplicate_id into canonical_id.
    """
    canonical = session.query(Movie).get(canonical_id)
    duplicate = session.query(Movie).get(duplicate_id)
    
    if not canonical or not duplicate:
        print(f"Error: One or both movies not found (ID {canonical_id}, ID {duplicate_id})")
        return False
        
    print(f"Merging ID {duplicate_id} ('{duplicate.title}') -> ID {canonical_id} ('{canonical.title}')")
    
    # 1. Update reviews
    reviews = session.query(Review).filter_by(movie_id=duplicate_id).all()
    for review in reviews:
        # Check if canonical already has a review from this critic
        existing = session.query(Review).filter_by(movie_id=canonical_id, critic_id=review.critic_id).first()
        if existing:
            print(f"  Warning: Critic {review.critic.name} already has a review for movie {canonical.title}. Deleting duplicate review from {review.publication.name}.")
            session.delete(review)
        else:
            print(f"  Updating review ID {review.id} from {review.publication.name} (critic: {review.critic.name}) to movie '{canonical.title}' (ID {canonical.id})")
            review.movie = canonical
            
    # 2. Merge metadata if canonical is missing it
    if not canonical.tmdb_id and duplicate.tmdb_id:
        canonical.tmdb_id = duplicate.tmdb_id
    if not canonical.imdb_id and duplicate.imdb_id:
        canonical.imdb_id = duplicate.imdb_id
    if not canonical.poster_url and duplicate.poster_url:
        canonical.poster_url = duplicate.poster_url
    if not canonical.letterboxd_url and duplicate.letterboxd_url:
        canonical.letterboxd_url = duplicate.letterboxd_url
    if not canonical.nytleffaan_url and duplicate.nytleffaan_url:
        canonical.nytleffaan_url = duplicate.nytleffaan_url
        
    # 3. Delete duplicate movie
    session.delete(duplicate)
    return True

def main():
    parser = argparse.ArgumentParser(description='Merge duplicate movies in the database.')
    parser.add_argument('--commit', action='store_true', help='Commit changes to the database.')
    args = parser.parse_args()
    
    engine = get_engine()
    session = get_session(engine)
    
    try:
        movies = session.query(Movie).order_by(Movie.id).all()
        
        seen_ids = set()
        to_merge = []
        
        for i, m1 in enumerate(movies):
            if m1.id in seen_ids:
                continue
                
            for m2 in movies[i+1:]:
                if m2.id in seen_ids:
                    continue
                    
                if are_same_movie(m1.title, m2.title):
                    # Pick the one with the longer name as canonical (usually better)
                    if len(m2.title) > len(m1.title):
                        canonical_id, duplicate_id = m2.id, m1.id
                    else:
                        canonical_id, duplicate_id = m1.id, m2.id
                    
                    print(f"Found match: '{m1.title}' (ID {m1.id}) and '{m2.title}' (ID {m2.id}). Canonical candidate: {canonical_id}")
                    to_merge.append((canonical_id, duplicate_id))
                    seen_ids.add(m1.id)
                    seen_ids.add(m2.id)
                    break 
            
            seen_ids.add(m1.id)

        if not to_merge:
            print("No duplicates found to merge.")
            return

        print(f"\nPlanned {len(to_merge)} merges:")
        for canonical_id, duplicate_id in to_merge:
            merge_movies(session, canonical_id, duplicate_id)
            
        if args.commit:
            session.commit()
            print("\nChanges committed to database.")
        else:
            print("\nDRY RUN: Changes not committed. Use --commit to apply changes.")
            session.rollback()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    main()
