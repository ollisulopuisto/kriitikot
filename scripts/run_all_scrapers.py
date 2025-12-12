#!/usr/bin/env python3
"""Run all scraper classes on bundled test HTML files and store new reviews.
This script is intended to be executed inside the project's virtual environment.
It uses the test data files located in ``tests/test_data``.
"""
import sys
from pathlib import Path

# Ensure the project src directory is on the import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scrapers import (
    HSScraper,
    KSMLScraper,
    ILScraper,
    TSScraper,
    SKScraper,
    ISScraper,
)
from models import get_session, Review

# Mapping of scraper class to its corresponding test HTML file
SCRAPER_FILES = {
    HSScraper: PROJECT_ROOT / "tests" / "test_data" / "hs_review_1.html",
    KSMLScraper: PROJECT_ROOT / "tests" / "test_data" / "ksml_review_1.html",
    ILScraper: PROJECT_ROOT / "tests" / "test_data" / "il_review_1.html",
    TSScraper: PROJECT_ROOT / "tests" / "test_data" / "ts_review_1.html",
    SKScraper: PROJECT_ROOT / "tests" / "test_data" / "sk_review_1.html",
    ISScraper: PROJECT_ROOT / "tests" / "test_data" / "is_review_1.html",
}


def run_scraper(scraper_cls, file_path: Path):
    scraper = scraper_cls()
    review = scraper.parse_file(str(file_path))
    return review


def main():
    session = get_session()
    added = 0
    for cls, path in SCRAPER_FILES.items():
        if not path.is_file():
            print(f"[WARN] Test file not found for {cls.__name__}: {path}")
            continue
        try:
            review = run_scraper(cls, path)
            if review:
                # Avoid duplicates based on source_url if present
                existing = (
                    session.query(Review)
                    .filter_by(source_url=review.source_url)
                    .first()
                )
                if not existing:
                    session.add(review)
                    added += 1
        except Exception as e:
            print(f"[ERROR] {cls.__name__} failed: {e}")
    session.commit()
    print(f"Added {added} new reviews to the database.")


if __name__ == "__main__":
    main()
