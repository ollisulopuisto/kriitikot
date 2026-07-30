
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import get_session, get_engine, Movie
from movie_normalizer import are_same_movie
from services.merge_service import merge_movies as merge_movie_records

def merge_movies(session, canonical_id, duplicate_id):
    """
    Merges movie with duplicate_id into canonical_id.
    """
    result = merge_movie_records(session, canonical_id, duplicate_id)

    if result is None:
        print(f"Error: One or both movies not found (ID {canonical_id}, ID {duplicate_id})")
        return False

    print(f"Merging ID {duplicate_id} ('{result.duplicate_title}') -> "
          f"ID {canonical_id} ('{result.canonical_title}')")
    print(f"  Moved {result.moved} review(s) to '{result.canonical_title}'")
    if result.dropped:
        print(f"  Deleted {result.dropped} review(s) whose critic already reviewed "
              f"'{result.canonical_title}'")
    if result.carried_metadata:
        print(f"  Carried over metadata: {', '.join(result.carried_metadata)}")

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
