
import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.scrapers.is_scraper import ISScraper

def debug():
    with open('/tmp/is_article.html', 'r', encoding='utf-8') as f:
        html = f.read()

    scraper = ISScraper()
    
    # 1. Parse full
    review = scraper.parse_html(html, "debug_url")
    print(f"Parse Result: {review}")
    if review:
        print(f"Title: {review.movie_title}")
        print(f"Source URL: {review.source_url}")
    
    # 2. Debug internals
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    if next_data_script:
        data = json.loads(next_data_script.string)
        asset_data = scraper._extract_asset_data(data)
        
        if asset_data:
            print("\n--- DEBUG INFO ---")
            print(f"Title: {asset_data.get('title')}")
            print(f"MetaTitle: {asset_data.get('metaTitle')}")
            
            is_review = scraper._is_movie_review(asset_data)
            print(f"Is Review: {is_review}")
            
            extracted_title = scraper._extract_movie_title(asset_data)
            print(f"Extracted Title: {extracted_title}")
            
            # Print keywords found
            text_content = scraper._get_full_text(asset_data).lower()
            
            # Print tags
            tags = asset_data.get('tags', [])
            print(f"Tags: {[t.get('title') for t in tags]}")

            streaming_keywords = [
                'katsomo+', 'katsomo +', 'mtv katsomo',
                'netflix', 'hbo', 'disney+', 'viaplay', 'ruutu',
                'suoratoistossa', 'suoratoistopalvelu',
                'tv:ssä', 'televisiossa'
            ]
            theater_keywords = [
                'elokuvateatter', 'valkokangas', 'teattereissa',
                'ensi-ilta', 'elokuvakino', 'finnkino'
            ]
            
            found_streaming = [kw for kw in streaming_keywords if kw in text_content]
            found_theater = [kw for kw in theater_keywords if kw in text_content]
            print(f"Found Streaming Keywords: {found_streaming}")
            print(f"Found Theater Keywords: {found_theater}")
            
            # Context for theater keywords
            if found_theater:
                print("Context for theater keywords:")
                for kw in found_theater:
                    idx = text_content.find(kw)
                    start = max(0, idx - 50)
                    end = min(len(text_content), idx + 50)
                    print(f"  '{kw}': ...{text_content[start:end]}...")

if __name__ == "__main__":
    debug()
