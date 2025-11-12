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
from metadata_fetcher import MetadataFetcher


def update_movie_metadata(movie: Movie, fetcher: MetadataFetcher) -> bool:
    """Update metadata for a single movie.

    Args:
        movie: Movie object to update
        fetcher: MetadataFetcher instance

    Returns:
        True if metadata was updated, False otherwise
    """
    updated = False

    try:
        print(f"  Processing: {movie.title}")

        # Fetch all metadata
        metadata = fetcher.fetch_all_metadata(movie.title)

        # Update TMDB data if not present
        if metadata.get('tmdb_data') and not movie.tmdb_id:
            tmdb_data = metadata['tmdb_data']
            movie.tmdb_id = tmdb_data.get('tmdb_id')
            movie.poster_url = tmdb_data.get('poster_url')
            print(f"    ✅ Added TMDB data (ID: {movie.tmdb_id})")
            updated = True

        # Update Letterboxd URL if not present
        if metadata.get('letterboxd_url') and not movie.letterboxd_url:
            movie.letterboxd_url = metadata['letterboxd_url']
            print(f"    ✅ Added Letterboxd URL")
            updated = True

        # Update Nytleffaan URL if not present
        if metadata.get('nytleffaan_url') and not movie.nytleffaan_url:
            movie.nytleffaan_url = metadata['nytleffaan_url']
            print(f"    ✅ Added Nytleffaan URL")
            updated = True

        if not updated:
            print("    ℹ️  No new metadata to add")

    except Exception as e:
        print(f"    ❌ Error updating metadata: {e}")

    return updated


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

        # Get all movies
        movies = session.query(Movie).all()
        total_movies = len(movies)

        print(f"📊 Processing {total_movies} movies...")
        print()

        # Track statistics
        updated_count = 0
        tmdb_added = 0
        letterboxd_added = 0
        nytleffaan_added = 0

        # Process each movie
        for i, movie in enumerate(movies, 1):
            print(f"[{i}/{total_movies}] ", end="")

            if update_movie_metadata(movie, fetcher):
                updated_count += 1

                # Count what was added
                if movie.tmdb_id:
                    tmdb_added += 1
                if movie.letterboxd_url:
                    letterboxd_added += 1
                if movie.nytleffaan_url:
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