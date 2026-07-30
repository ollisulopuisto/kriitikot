#!/usr/bin/env python3
"""
Update metadata for all movies in the database.

This script fetches TMDB data, Letterboxd URLs, and Nytleffaan URLs
for movies that don't have this metadata yet.
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import get_session, Movie
from metadata_fetcher import MetadataFetcher, backfill_movie_metadata


def update_movie_metadata(movie: Movie, fetcher: MetadataFetcher) -> bool:
    """Update metadata for a single movie.

    Args:
        movie: Movie object to update
        fetcher: MetadataFetcher instance

    Returns:
        True if metadata was updated, False otherwise
    """
    try:
        print(f"  Processing: {movie.title}")
        added = backfill_movie_metadata(movie, fetcher)

        if added:
            print(f"    ✅ Added: {', '.join(added)}")
        else:
            print("    ℹ️  No new metadata to add")

        return bool(added)

    except Exception as e:
        print(f"    ❌ Error updating metadata: {e}")
        return False


def needs_metadata_backfill(movie: Movie) -> bool:
    """Return True when movie is missing at least one metadata field."""
    return not movie.tmdb_id or not movie.poster_url or not movie.letterboxd_url or not movie.nytleffaan_url


def main():
    """Main function to update metadata for all movies."""
    print("=" * 60)
    print("🎬 UPDATE MOVIE METADATA")
    print("=" * 60)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Initialize
        session = get_session()
        fetcher = MetadataFetcher()

        # Process only movies that are missing metadata
        movies = [movie for movie in session.query(Movie).all() if needs_metadata_backfill(movie)]
        total_movies = len(movies)

        print(f"📊 Processing {total_movies} movies missing metadata...")
        print()

        # Track statistics
        updated_count = 0
        tmdb_added = 0
        posters_added = 0
        letterboxd_added = 0
        nytleffaan_added = 0

        # Process each movie
        for i, movie in enumerate(movies, 1):
            print(f"[{i}/{total_movies}] ", end="")
            had_tmdb = bool(movie.tmdb_id)
            had_poster = bool(movie.poster_url)
            had_letterboxd = bool(movie.letterboxd_url)
            had_nytleffaan = bool(movie.nytleffaan_url)

            if update_movie_metadata(movie, fetcher):
                updated_count += 1

                # Count only newly added metadata fields
                if not had_tmdb and movie.tmdb_id:
                    tmdb_added += 1
                if not had_poster and movie.poster_url:
                    posters_added += 1
                if not had_letterboxd and movie.letterboxd_url:
                    letterboxd_added += 1
                if not had_nytleffaan and movie.nytleffaan_url:
                    nytleffaan_added += 1

        # Commit all changes
        session.commit()

        # Final statistics
        print()
        print("=" * 60)
        print("✅ METADATA UPDATE COMPLETE")
        print("=" * 60)
        print(f"📈 Movies updated: {updated_count}/{total_movies}")
        print(f"🎭 TMDB IDs added: {tmdb_added}")
        print(f"🖼️ Posters added: {posters_added}")
        print(f"📝 Letterboxd URLs added: {letterboxd_added}")
        print(f"🎫 Nytleffaan URLs added: {nytleffaan_added}")
        print(f"⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()


if __name__ == '__main__':
    main()
