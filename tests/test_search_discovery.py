import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from generate_static import write_discovery_files  # noqa: E402


def test_robots_allows_all_crawlers_and_points_to_sitemap(tmp_path):
    write_discovery_files(tmp_path)
    robots = (tmp_path / 'robots.txt').read_text(encoding='utf-8')
    assert 'User-agent: *\nAllow: /' in robots
    assert 'Disallow' not in robots
    assert 'Sitemap: https://kriitikot.sulopuis.to/sitemap.xml' in robots


def test_sitemap_lists_canonical_url(tmp_path):
    write_discovery_files(tmp_path)
    sitemap = (tmp_path / 'sitemap.xml').read_text(encoding='utf-8')
    assert '<loc>https://kriitikot.sulopuis.to/</loc>' in sitemap


def test_index_has_canonical_and_structured_data():
    html = Path('templates/index.html').read_text(encoding='utf-8')
    assert '<link rel="canonical" href="https://kriitikot.sulopuis.to/">' in html
    assert 'application/ld+json' in html
    assert 'ollisulopuisto.github.io' not in html


def test_llms_txt_describes_site_and_data(tmp_path):
    write_discovery_files(tmp_path)
    llms = (tmp_path / 'llms.txt').read_text(encoding='utf-8')
    assert llms.startswith('# Kriitikon valinta\n\n> ')
    assert 'https://kriitikot.sulopuis.to/reviews.json' in llms
    assert 'https://kriitikot.sulopuis.to/rss.xml' in llms
