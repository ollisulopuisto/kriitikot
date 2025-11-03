#!/usr/bin/env python3
"""
Testaa metatietojen hakua vuosipreferenssillä.
"""

import sys
sys.path.insert(0, 'src')

from metadata_fetcher import MetadataFetcher
from datetime import datetime

def test_year_preference():
    """Testaa että uudemmat elokuvat valitaan."""
    fetcher = MetadataFetcher()
    current_year = datetime.now().year
    
    # Testaa elokuvia joista on useita versioita
    test_movies = [
        "Dune",  # On sekä 1984, 2000 että 2021 versio
        "The Batman",  # Useita Batman-elokuvia
        "Joker",  # 2019
    ]
    
    print(f"🎬 Testataan metatietojen hakua (vuosi: {current_year})")
    print("=" * 70)
    
    for movie_title in test_movies:
        print(f"\n📽️  Elokuva: {movie_title}")
        print("-" * 70)
        
        # Hae TMDB data
        tmdb_result = fetcher.search_movie_tmdb(movie_title, prefer_recent=True)
        if tmdb_result:
            release_year = tmdb_result.get('release_date', '')[:4] if tmdb_result.get('release_date') else 'N/A'
            print(f"   TMDB: {tmdb_result.get('title')} ({release_year})")
            print(f"   TMDB ID: {tmdb_result.get('tmdb_id')}")
            poster_url = tmdb_result.get('poster_url') or 'N/A'
            if poster_url != 'N/A':
                print(f"   Poster: {poster_url[:60]}...")
            else:
                print(f"   Poster: {poster_url}")
        else:
            print("   TMDB: Ei löytynyt")
        
        # Hae Letterboxd URL
        letterboxd_url = fetcher.search_movie_letterboxd(movie_title, prefer_recent=True)
        if letterboxd_url:
            print(f"   Letterboxd: {letterboxd_url}")
        else:
            print("   Letterboxd: Ei löytynyt")
        
        # Hae Nytleffaan URL
        nytleffaan_url = fetcher.search_movie_nytleffaan(movie_title, prefer_recent=True)
        if nytleffaan_url:
            print(f"   Nytleffaan: {nytleffaan_url}")
        else:
            print("   Nytleffaan: Ei löytynyt")
    
    print("\n" + "=" * 70)
    print("✅ Testit suoritettu!")
    print("\n💡 Huom: Tarkista että TMDB palauttaa uusimmat versiot elokuvista,")
    print("   ei vanhoja (esim. Dune 2021 eikä Dune 1984)")

if __name__ == '__main__':
    test_year_preference()
