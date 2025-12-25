
import sys
import os
import json
from bs4 import BeautifulSoup

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from scrapers.is_scraper import ISScraper

def debug(filename):
    scraper = ISScraper()
    print(f"Debugging file: {filename}")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Could not read file: {e}")
        return

    soup = BeautifulSoup(content, 'html.parser')
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    
    if not next_data_script:
        print("FAIL: __NEXT_DATA__ script not found")
        return

    try:
        data = json.loads(next_data_script.string)
    except Exception as e:
        print(f"FAIL: JSON decode error: {e}")
        return

    asset_data = scraper._extract_asset_data(data)
    if not asset_data:
        print("FAIL: asset_data not found")
        return

    full_text = scraper._get_full_text(asset_data).lower()
    
    phrase = "tv-lehti arvioi"
    if phrase in full_text:
        print(f"FOUND PHRASE: '{phrase}'")
        # Print context
        idx = full_text.find(phrase)
        print(f"Context: ...{full_text[idx:idx+50]}...")
    else:
        print(f"PHRASE NOT FOUND: '{phrase}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug(sys.argv[1])
    else:
        print("Usage: python debug_phrase.py <filename>")
