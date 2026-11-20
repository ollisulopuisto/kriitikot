"""Template contract for the compact toolbar; real geometry is checked in Chrome."""

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


def toolbar():
    env = Environment(loader=FileSystemLoader("templates"))
    html = env.get_template("index.html").render(
        grouped_reviews={},
        all_critics=[],
        pub_stats={
            name: 1
            for name in (
                "DEMOKRAATTI",
                "EPISODI",
                "FILMOHOLIC",
                "HS",
                "IL",
                "IS",
                "KSML",
                "KULTTUURITOIMITUS",
                "MUROPAKETTI",
                "SK",
                "TS",
            )
        },
        nytleffaan_urls={},
        letterboxd_urls={},
        poster_urls={},
        movie_review_counts={},
        movie_rating_distributions={},
        total_reviews=0,
    )
    return BeautifulSoup(html, "html.parser")


def test_sorting_and_reset_have_separate_rows():
    bar = toolbar().select_one(".desktop-filters")
    assert (
        bar.select_one(".sorting-group #sort-movies-btn").get_text(strip=True)
        == "Elokuvat A–Ö"
    )
    assert (
        bar.select_one(".sorting-group #sort-critics-btn").get_text(strip=True)
        == "Kriitikot A–Ö"
    )
    assert bar.select_one(".group-favorites #reset-filters-desktop")
    assert not bar.select_one(".sorting-group #reset-filters-desktop")


def test_favourites_toggle_has_clickable_accessible_labels():
    soup = toolbar()
    for device in ("desktop", "mobile"):
        checkbox = soup.select_one(f"#favorites-toggle-{device}")
        assert checkbox.find_parent("label").get_text(strip=True) == "Suosikkikriitikot"


def test_all_publications_and_slider_contracts_survive_relayout():
    soup = toolbar()
    for selector in (".desktop-filters", ".mobile-filter"):
        buttons = soup.select(f"{selector} .filter-publication")
        assert len(buttons) == 11
        assert len({b["data-publication"] for b in buttons}) == 11
    for slider_id in ("min-reviews-slider", "star-filter-slider"):
        slider = soup.select_one(f"#{slider_id}")
        assert (slider["min"], slider["max"], slider["step"]) == ("1", "5", "1")
        assert soup.select_one(f'label[for="{slider_id}"]')
        assert (
            len(slider.find_parent(class_="filter-group").select(".slider-labels span"))
            == 5
        )
