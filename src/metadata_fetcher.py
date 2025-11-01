#!/usr/bin/env python3
"""
Elokuvan metatietojen hakija.

Hakee tietoja TMDB:stä, Letterboxd:sta ja Nytleffaan.fi:stä.
"""

import requests
import json
import re
from typing import Dict, Optional, Tuple
import os
import sys

# Lisää src-hakemisto polkuun
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Movie
from config import TMDB_API_KEY


class MetadataFetcher:
    """Hakee elokuvan metatietoja eri lähteistä."""
    
    def __init__(self):
        self.tmdb_api_key = TMDB_API_KEY
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.tmdb_image_base_url = "https://image.tmdb.org/t/p/w500"  # Keskitason koko julisteille
        
    def search_movie_tmdb(self, movie_title: str) -> Optional[Dict]:
        """Hae elokuva TMDB:stä nimellä.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Dict elokuvan tiedoilla tai None jos ei löydy
        """
        try:
            url = f"{self.tmdb_base_url}/search/movie"
            params = {
                'api_key': self.tmdb_api_key,
                'query': movie_title,
                'language': 'fi-FI'  # Suomipainotteinen
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                # Palauta ensimmäinen osuma (yleensä paras)
                movie = data['results'][0]
                return {
                    'tmdb_id': movie['id'],
                    'title': movie['title'],
                    'original_title': movie.get('original_title', ''),
                    'release_date': movie.get('release_date', ''),
                    'poster_path': movie.get('poster_path'),
                    'overview': movie.get('overview', ''),
                    'vote_average': movie.get('vote_average', 0),
                    'poster_url': self.tmdb_image_base_url + movie['poster_path'] if movie.get('poster_path') else None
                }
            
        except Exception as e:
            print(f"TMDB search error for '{movie_title}': {e}")
        
        return None
    
    def get_movie_details_tmdb(self, tmdb_id: int) -> Optional[Dict]:
        """Hae elokuvan yksityiskohdat TMDB ID:llä.
        
        Args:
            tmdb_id: TMDB elokuva ID
            
        Returns:
            Dict yksityiskohtaisilla tiedoilla
        """
        try:
            url = f"{self.tmdb_base_url}/movie/{tmdb_id}"
            params = {
                'api_key': self.tmdb_api_key,
                'language': 'fi-FI'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            movie = response.json()
            
            return {
                'tmdb_id': movie['id'],
                'title': movie['title'],
                'original_title': movie.get('original_title', ''),
                'release_date': movie.get('release_date', ''),
                'poster_path': movie.get('poster_path'),
                'backdrop_path': movie.get('backdrop_path'),
                'overview': movie.get('overview', ''),
                'vote_average': movie.get('vote_average', 0),
                'genres': [g['name'] for g in movie.get('genres', [])],
                'runtime': movie.get('runtime'),
                'poster_url': self.tmdb_image_base_url + movie['poster_path'] if movie.get('poster_path') else None,
                'backdrop_url': f"https://image.tmdb.org/t/p/w1280{movie['backdrop_path']}" if movie.get('backdrop_path') else None
            }
            
        except Exception as e:
            print(f"TMDB details error for ID {tmdb_id}: {e}")
        
        return None
    
    def search_movie_letterboxd(self, movie_title: str) -> Optional[str]:
        """Hae Letterboxd-linkki elokuvalle.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Letterboxd URL tai None
        """
        try:
            # Yritä muodostaa URL suoraan (usein toimii)
            # Muunna nimi URL-ystävälliseksi
            slug = re.sub(r'[^\w\s-]', '', movie_title.lower())
            slug = re.sub(r'[\s]+', '-', slug)
            
            url = f"https://letterboxd.com/film/{slug}/"
            
            # Tarkista että sivu löytyy
            response = requests.head(url, timeout=5)
            
            if response.status_code == 200:
                return url
            
            # Jos ei löydy, yritä hakua
            search_url = f"https://letterboxd.com/search/films/{slug}/"
            response = requests.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Etsi ensimmäinen film-linkki
                match = re.search(r'href="(/film/[^"]*)"', response.text)
                if match:
                    return f"https://letterboxd.com{match.group(1)}"
            
        except Exception as e:
            print(f"Letterboxd search error for '{movie_title}': {e}")
        
        return None
    
    def search_movie_nytleffaan(self, movie_title: str) -> Optional[str]:
        """Hae Nytleffaan.fi-linkki elokuvalle.
        
        Koska sivusto käyttää bot protectionia, käytetään direct URL muodostamista
        perustuen elokuvan nimeen.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Nytleffaan.fi elokuva-sivu URL tai None
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Muunna nimi URL-ystävälliseksi slugiksi
            # Nytleffaan.fi käyttää erikoista muunnosta: ä→A, ö→O (isoilla kirjaimilla!)
            slug = movie_title.lower()
            
            # Translitteroi suomalaiset ääkköset Nytleffaan.fi:n tapaan
            transliteration_map = {
                'ä': 'A',
                'ö': 'O',
                'å': 'a',
                'Ä': 'A',
                'Ö': 'O',
                'Å': 'a'
            }
            
            for finnish_char, replacement in transliteration_map.items():
                slug = slug.replace(finnish_char, replacement)
            
            # Poista erikoismerkit ja välilyönnit
            slug = re.sub(r'[^\w\s-]', '', slug)
            slug = re.sub(r'[\s]+', '', slug)
            
            # Yritä muodostaa URL suoraan
            direct_url = f"https://www.nytleffaan.fi/elokuva/{slug}/"
            
            # Tarkista että sivu löytyy (hyväksy myös 202 status bot protection vuoksi)
            check_response = requests.head(direct_url, headers=headers, timeout=5)
            
            if check_response.status_code < 400:  # Accept 200, 202, etc.
                return direct_url
            
            # Jos ei löydy, yritä vaihtoehtoisia slug-muotoja
            # Esim. lisää vuosi jos tiedossa, tai muuta väliviivat
            alt_slug = re.sub(r'[^\w\s-]', '', movie_title.lower())
            alt_slug = re.sub(r'[\s]+', '-', alt_slug)  # Käytä väliviivoja
            
            alt_url = f"https://www.nytleffaan.fi/elokuva/{alt_slug}/"
            check_response = requests.head(alt_url, headers=headers, timeout=5)
            
            if check_response.status_code < 400:
                return alt_url
            
        except Exception as e:
            print(f"Nytleffaan search error for '{movie_title}': {e}")
        
        return None
    
    def fetch_all_metadata(self, movie_title: str) -> Dict:
        """Hae kaikki metatiedot elokuvalle.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Dict kaikilla löydetyillä metatiedoilla
        """
        result = {
            'title': movie_title,
            'tmdb_data': None,
            'letterboxd_url': None,
            'nytleffaan_url': None
        }
        
        # TMDB
        tmdb_data = self.search_movie_tmdb(movie_title)
        if tmdb_data:
            result['tmdb_data'] = tmdb_data
        
        # Letterboxd
        letterboxd_url = self.search_movie_letterboxd(movie_title)
        if letterboxd_url:
            result['letterboxd_url'] = letterboxd_url
        
        # Nytleffaan
        nytleffaan_url = self.search_movie_nytleffaan(movie_title)
        if nytleffaan_url:
            result['nytleffaan_url'] = nytleffaan_url
        
        return result


def test_metadata_fetcher():
    """Testaa metadata fetcheria."""
    fetcher = MetadataFetcher()
    
    # Testaa tunnetulla elokuvalla
    movie_title = "Inception"
    
    print(f"Haetaan metatietoja elokuvalle: {movie_title}")
    print("-" * 50)
    
    result = fetcher.fetch_all_metadata(movie_title)
    
    print(f"TMDB data: {result['tmdb_data'] is not None}")
    if result['tmdb_data']:
        print(f"  Title: {result['tmdb_data']['title']}")
        print(f"  TMDB ID: {result['tmdb_data']['tmdb_id']}")
        print(f"  Poster URL: {result['tmdb_data']['poster_url']}")
    
    print(f"Letterboxd URL: {result['letterboxd_url']}")
    print(f"Nytleffaan URL: {result['nytleffaan_url']}")


def test_nytleffaan():
    """Testaa nytleffaan.fi hakua."""
    fetcher = MetadataFetcher()
    
    test_movies = ["Black Phone 2", "Inception", "Oppenheimer"]
    
    for movie in test_movies:
        print(f"\nTestataan: {movie}")
        url = fetcher.search_movie_nytleffaan(movie)
        print(f"Tulos: {url}")
        
        if url:
            # Testaa että URL toimii (hyväksy myös 202 status)
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.head(url, headers=headers, timeout=5)
                print(f"URL status: {response.status_code} (hyväksyttävä: {response.status_code < 400})")
            except Exception as e:
                print(f"URL error: {e}")


if __name__ == '__main__':
    test_metadata_fetcher()
    test_nytleffaan()