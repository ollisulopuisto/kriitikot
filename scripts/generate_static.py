#!/usr/bin/env python3
"""
Generoi staattiset HTML-sivut Flask-appista GitHub Pagesille.

Käyttö:
    python scripts/generate_static.py
"""

import shutil
import sys
from pathlib import Path

# Lisää src kansio Python pathiin
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from app import app, get_all_reviews_grouped, APP_VERSION

def generate_static_site():
    """Generoi staattiset sivut docs/ kansioon."""
    
    # Luo docs kansio (GitHub Pages käyttää tätä)
    docs_dir = Path(__file__).parent.parent / 'docs'
    docs_dir.mkdir(exist_ok=True)
    
    print(f"📝 Generoidaan staattinen sivusto (versio {APP_VERSION})...")
    
    # 1. Renderöi pääsivu
    with app.app_context():
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                index_html = docs_dir / 'index.html'
                index_html.write_bytes(response.data)
                print(f"✅ Luotu: {index_html}")
            else:
                print(f"❌ Virhe index.html: HTTP {response.status_code}")
                return False

            # Renderöi RSS
            response = client.get('/rss.xml')
            if response.status_code == 200:
                rss_xml = docs_dir / 'rss.xml'
                rss_xml.write_bytes(response.data)
                print(f"✅ Luotu: {rss_xml}")
            else:
                print(f"❌ Virhe rss.xml: HTTP {response.status_code}")
                # Ei katkaista prosessia vaikka RSS epäonnistuisi, mutta hyvä logata
    
    # 2. Kopioi static-kansio
    src_static = Path(__file__).parent.parent / 'static'
    dst_static = docs_dir / 'static'
    
    if dst_static.exists():
        shutil.rmtree(dst_static)
    
    shutil.copytree(src_static, dst_static)
    print("✅ Kopioitu: static/ -> docs/static/")
    
    # 3. Luo .nojekyll tiedosto (GitHub Pages ei käsittele Jekylliä)
    nojekyll = docs_dir / '.nojekyll'
    nojekyll.touch()
    print(f"✅ Luotu: {nojekyll}")
    
    # 4. Tilastot
    grouped_reviews, all_critics, total_reviews = get_all_reviews_grouped()
    
    print("\n📊 Sivuston tilastot:")
    print(f"   - Elokuvia: {len(grouped_reviews)}")
    print(f"   - Kriitikoita: {len(all_critics)}")
    print(f"   - Arvosteluja: {total_reviews}")
    
    print(f"\n✨ Staattinen sivusto valmis: {docs_dir}")
    print("\n📌 Seuraavat vaiheet:")
    print("   1. git add docs/")
    print("   2. git commit -m 'Päivitä staattiset sivut'")
    print("   3. git push")
    print("   4. GitHub Settings -> Pages -> Source: main branch, /docs folder")
    
    return True

if __name__ == '__main__':
    success = generate_static_site()
    sys.exit(0 if success else 1)
