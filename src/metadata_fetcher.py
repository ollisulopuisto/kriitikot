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
        
    def search_movie_tmdb(self, movie_title: str, prefer_recent: bool = True) -> Optional[Dict]:
        """Hae elokuva TMDB:stä nimellä.
        
        Args:
            movie_title: Elokuvan nimi
            prefer_recent: Jos True, suosii tuoreita elokuvia (oletuksena True)
            
        Returns:
            Dict elokuvan tiedoilla tai None jos ei löydy
        """
        from datetime import datetime
        
        try:
            url = f"{self.tmdb_base_url}/search/movie"
            base_params = {
                'api_key': self.tmdb_api_key,
                'query': movie_title,
                'language': 'fi-FI'  # Suomipainotteinen
            }
            
            # Jos halutaan suosia tuoreita elokuvia, kokeile ensin viime vuosien elokuvia
            if prefer_recent:
                current_year = datetime.now().year
                
                # Kokeile ensin nykyinen vuosi, sitten edellinen
                for year_offset in [0, 1]:  # 2025, 2024
                    try_year = current_year - year_offset
                    params = base_params.copy()
                    params['primary_release_year'] = try_year
                    
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get('results') and len(data['results']) > 0:
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
            
            # Jos ei löytynyt vuosien perusteella, hae ilman vuotta
            response = requests.get(url, params=base_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                # Järjestä tulokset julkaisuvuoden mukaan (uusin ensin) jos prefer_recent
                if prefer_recent:
                    results = data['results']
                    
                    results_with_year = []
                    for movie in results:
                        release_date = movie.get('release_date', '')
                        if release_date:
                            try:
                                year = int(release_date[:4])
                                results_with_year.append((movie, year))
                            except (ValueError, IndexError):
                                results_with_year.append((movie, 0))
                        else:
                            results_with_year.append((movie, 0))
                    
                    # Järjestä vuoden mukaan laskevasti (uusin ensin)
                    results_with_year.sort(key=lambda x: x[1], reverse=True)
                    movie = results_with_year[0][0]
                else:
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
                'language': 'fi-FI',
                'append_to_response': 'external_ids'  # Hae myös IMDB ID
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            movie = response.json()
            
            # Hae IMDB ID external_ids:stä
            imdb_id = None
            if 'external_ids' in movie:
                imdb_id = movie['external_ids'].get('imdb_id')
            
            return {
                'tmdb_id': movie['id'],
                'imdb_id': imdb_id,
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
    
    def get_poster_by_tmdb_id(self, tmdb_id: str) -> Optional[str]:
        """Hae elokuvan juliste TMDB ID:n perusteella.
        
        Args:
            tmdb_id: TMDB elokuva ID (voi olla string tai int)
            
        Returns:
            Julisteen URL tai None
        """
        try:
            # Varmista että ID on numero
            numeric_id = int(tmdb_id)
            details = self.get_movie_details_tmdb(numeric_id)
            
            if details and details.get('poster_url'):
                return details['poster_url']
                
        except (ValueError, TypeError) as e:
            print(f"Invalid TMDB ID '{tmdb_id}': {e}")
        except Exception as e:
            print(f"Error fetching poster for TMDB ID {tmdb_id}: {e}")
        
        return None
    
    def fetch_tmdb_data(self, movie_title: str) -> Optional[Dict]:
        """Hae TMDB data elokuvan nimellä.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Dict TMDB datalla (sisältää myös imdb_id:n)
        """
        movie_data = self.search_movie_tmdb(movie_title)
        
        if movie_data and movie_data.get('tmdb_id'):
            # Hae lisätiedot (ml. IMDB ID)
            details = self.get_movie_details_tmdb(movie_data['tmdb_id'])
            if details:
                return details
        
        return movie_data
    
    def generate_letterboxd_url(self, movie_title: str) -> Optional[str]:
        """Generoi Letterboxd URL elokuvan nimestä.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Letterboxd URL
        """
        return self.search_movie_letterboxd(movie_title)
    
    def generate_nytleffaan_url(self, movie_title: str) -> Optional[str]:
        """Generoi Nytleffaan URL elokuvan nimestä.
        
        Args:
            movie_title: Elokuvan nimi
            
        Returns:
            Nytleffaan URL
        """
        return self.search_movie_nytleffaan(movie_title)
    
    def search_movie_letterboxd(self, movie_title: str, prefer_recent: bool = True) -> Optional[str]:
        """Hae Letterboxd-linkki elokuvalle.
        
        Args:
            movie_title: Elokuvan nimi
            prefer_recent: Jos True, yritä ensin nykyisen vuoden elokuvaa
            
        Returns:
            Letterboxd URL tai None
        """
        from datetime import datetime
        
        try:
            # Yritä muodostaa URL suoraan (usein toimii)
            # Muunna nimi URL-ystävälliseksi
            slug = re.sub(r'[^\w\s-]', '', movie_title.lower())
            slug = re.sub(r'[\s]+', '-', slug)
            
            # Jos halutaan suosia tuoreita elokuvia, yritä ensin vuoden kanssa
            if prefer_recent:
                current_year = datetime.now().year
                url_with_year = f"https://letterboxd.com/film/{slug}-{current_year}/"
                
                try:
                    response = requests.head(url_with_year, timeout=5)
                    if response.status_code == 200:
                        return url_with_year
                except:
                    pass  # Jatka ilman vuotta
            
            # Yritä ilman vuotta
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
    
    def search_movie_nytleffaan(self, movie_title: str, prefer_recent: bool = True) -> Optional[str]:
        """Hae Nytleffaan.fi-linkki elokuvalle.
        
        Koska sivusto käyttää bot protectionia, käytetään direct URL muodostamista
        perustuen elokuvan nimeen.
        
        Args:
            movie_title: Elokuvan nimi
            prefer_recent: Jos True, yritä ensin nykyisen vuoden elokuvaa
            
        Returns:
            Nytleffaan.fi elokuva-sivu URL tai None
        """
        from datetime import datetime
        
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
            
            # Jos halutaan suosia tuoreita elokuvia, yritä ensin vuoden kanssa
            if prefer_recent:
                current_year = datetime.now().year
                year_url = f"https://www.nytleffaan.fi/elokuva/{slug}{current_year}/"
                
                try:
                    check_response = requests.head(year_url, headers=headers, timeout=5)
                    if check_response.status_code < 400:
                        return year_url
                except:
                    pass  # Jatka ilman vuotta
            
            # Yritä muodostaa URL suoraan ilman vuotta
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
        
        # TMDB (käytä fetch_tmdb_data joka hakee myös IMDB ID:n)
        tmdb_data = self.fetch_tmdb_data(movie_title)
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