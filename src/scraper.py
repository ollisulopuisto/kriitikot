
import json
from bs4 import BeautifulSoup

def scrape_hs_review(file_path: str) -> dict:
    """
    Parsii yksittäisen HS.fi-arvostelun HTML-tiedostosta.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    if not next_data_script:
        return {}
        
    data = json.loads(next_data_script.string)
    page_props = data.get('props', {}).get('pageProps', {})
    page = page_props.get('page', {})
    page_data = page.get('data', {})

    if isinstance(page_data, dict):
        nested_data = page_data.get('data', [])
        if isinstance(nested_data, list) and nested_data:
            for lane_container in nested_data:
                lanes = lane_container.get('lanes', [])
                for lane in lanes:
                    items = lane.get('items', [])
                    for item in items:
                        if item.get('itemType') == 'standard' and item.get('theme') != 'advertorial':
                            return item  # Palautetaan koko item-sanakirja

    return {}
