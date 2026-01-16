
import sys
import os
import requests
sys.path.insert(0, 'src')
from scrapers.kulttuuritoimitus import KulttuuritoimitusScraper

def reproduce():
    url = "https://kulttuuritoimitus.fi/kritiikit/kritiikit-elokuva/inkerin-railin-kertun-ja-matin-matka-oman-maailman-ympari-on-varikas-arviossa-terasleidit-elokuva-kuin-viimeista-paivaa/"
    output_file = "tests/test_data/kulttuuritoimitus_repro.html"
    
    # Download HTML
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
        
    print(f"Downloaded HTML to {output_file}")
    
    # additional debug info on the infobox
    if "Teräsleidit" in response.text:
         print("Found 'Teräsleidit' in response text")
    
    # Run scraper
    scraper = KulttuuritoimitusScraper()
    review = scraper.parse_html(response.text, source_url=url)
    
    print("\nParsed Review:")
    print(f"Title: {review.movie_title}")
    print(f"Critic: {review.critic_name}")
    print(f"Rating: {review.rating_stars}")
    
    expected_title = "Teräsleidit – Kuin viimeistä päivää"
    if review.movie_title != expected_title:
        print(f"\nFAILURE: Expected title '{expected_title}', got '{review.movie_title}'")
        sys.exit(1)
    else:
        print("\nSUCCESS: correct title extracted")

if __name__ == "__main__":
    reproduce()
