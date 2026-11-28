import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_page_css_and_js_url_carries_its_content_hash():
    from app import app
    html = app.jinja_env.get_template('index.html').render(grouped_reviews={}, all_critics=[], pub_stats={}, nytleffaan_urls={}, letterboxd_urls={}, poster_urls={}, movie_review_counts={}, movie_rating_distributions={}, total_reviews=0)
    refs = re.findall(r'(?:src|href)="(static/[^"?]+\.(?:css|js))(?:\?v=([a-f0-9]+))?"', html)
    assert len(refs) == 11
    for path, version in refs:
        assert version == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:16], path


def test_asset_url_changes_only_when_that_file_changes(tmp_path):
    from asset_urls import asset_url
    target = tmp_path / 'ui.js'
    target.write_text('first')
    first = asset_url(tmp_path, 'ui.js')
    target.write_text('second')
    assert asset_url(tmp_path, 'ui.js') != first
    assert asset_url(tmp_path, 'ui.js') == asset_url(tmp_path, 'ui.js')


def test_checked_in_docs_asset_urls_match_shipped_contents():
    html = (ROOT / 'docs/index.html').read_text()
    refs = re.findall(r'(?:src|href)="(static/[^"?]+\.(?:css|js))(?:\?v=([a-f0-9]+))?"', html)
    assert len(refs) == 11
    for path, version in refs:
        assert version == hashlib.sha256((ROOT / 'docs' / path).read_bytes()).hexdigest()[:16], path
