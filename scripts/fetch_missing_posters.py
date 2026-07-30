#!/usr/bin/env python3
"""
Fetch missing posters for movies from TMDB.

Usage:
    python scripts/fetch_missing_posters.py <TMDB_API_KEY>
    
Or with environment variable:
    export TMDB_API_KEY=your_key_here
    python scripts/fetch_missing_posters.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import get_session, Movie
from metadata_fetcher import MetadataFetcher


def main():
    # Get API key from argument or environment
    if len(sys.argv) > 1:
        os.environ['TMDB_API_KEY'] = sys.argv[1]

    fetcher = MetadataFetcher()
    if not fetcher.tmdb_api_key:
        fetcher.tmdb_api_key = os.environ.get('TMDB_API_KEY')

    if not fetcher.tmdb_api_key:
        print("Error: TMDB API key required")
        print("Usage: python scripts/fetch_missing_posters.py <TMDB_API_KEY>")
        print("Or set TMDB_API_KEY environment variable")
        sys.exit(1)

    session = get_session()
    
    # Find movies without posters
    movies_without_posters = session.query(Movie).filter(
        (Movie.poster_url == None) | (Movie.poster_url == '')
    ).all()
    
    total_movies = session.query(Movie).count()
    
    print(f"📊 Total movies: {total_movies}")
    print(f"🎬 Movies without posters: {len(movies_without_posters)}")
    print()
    
    if not movies_without_posters:
        print("✅ All movies have posters!")
        session.close()
        return
    
    updated = 0
    failed = []
    
    for movie in movies_without_posters:
        print(f"🔍 Searching: {movie.title}")

        # Try exact title first
        result = fetcher.search_movie_tmdb(movie.title)
        
        if result and result.get('poster_url'):
            print(f"  ✅ Found: {result['title']} ({result['release_date']})")
            print(f"     Poster: {result['poster_url']}")
            
            movie.poster_url = result['poster_url']
            
            # Also save TMDB ID if we don't have it
            if not movie.tmdb_id and result.get('tmdb_id'):
                movie.tmdb_id = result['tmdb_id']
            
            updated += 1
        else:
            print(f"  ❌ No poster found")
            failed.append(movie.title)
        
        print()
    
    # Commit all changes
    session.commit()
    session.close()
    
    print("=" * 60)
    print(f"✅ Updated {updated} movies")
    
    if failed:
        print(f"❌ Failed to find posters for {len(failed)} movies:")
        for title in failed:
            print(f"   - {title}")
        print()
        print("💡 Tip: Try manual search with different queries at TMDB.org")


if __name__ == '__main__':
    main()
