import importlib.util
import sqlite3
from pathlib import Path

import pytest
from scrapers.is_scraper import ISScraper

spec = importlib.util.spec_from_file_location('is_repair', Path(__file__).parents[1] / 'scripts/repair_is_yon_lapsi.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    c = sqlite3.connect(':memory:')
    c.executescript('''CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT);
    CREATE TABLE publications(id INTEGER PRIMARY KEY,short_name TEXT);
    CREATE TABLE reviews(id INTEGER PRIMARY KEY,movie_id INTEGER REFERENCES movies(id),critic_id INTEGER,
      review_text TEXT,publication_id INTEGER,source_url TEXT, rating INTEGER);
    INSERT INTO movies VALUES(348,'Yön Lapsi'),(351,'Harry Potter');
    INSERT INTO publications VALUES(6,'is');''')
    c.execute('INSERT INTO reviews VALUES(1087,351,12,?,6,?,2)', ('Yön lapsi, ensi-ilta perjantaina', module.URL))
    c.commit()
    return c


def test_exact_link_only_dry_run_apply_and_idempotency():
    c = fixture()
    before = c.execute('SELECT * FROM reviews').fetchall()
    movies = c.execute('SELECT * FROM movies').fetchall()
    assert module.repair(c) == [(1087,351,348)]
    assert c.execute('SELECT * FROM reviews').fetchall() == before
    assert module.repair(c, True) == [(1087,351,348)]
    after = c.execute('SELECT * FROM reviews').fetchall()
    assert after == [(before[0][0],348,*before[0][2:])]
    assert c.execute('SELECT * FROM movies').fetchall() == movies
    assert module.repair(c, True) == []


@pytest.mark.parametrize('change', [
    "UPDATE movies SET title='other' WHERE id=348",
    "UPDATE reviews SET source_url='other'",
    "UPDATE reviews SET review_text='other'",
    "UPDATE reviews SET movie_id=999",
    "INSERT INTO reviews VALUES(999,348,12,'other',6,'other',4)",
])
def test_changed_identity_or_conflict_aborts(change):
    c = fixture(); c.execute(change); c.commit()
    before = c.execute('SELECT * FROM reviews').fetchall()
    with pytest.raises(ValueError): module.repair(c, True)
    assert c.execute('SELECT * FROM reviews').fetchall() == before


def test_current_parser_prefers_film_endnote_over_incidental_italic_franchise():
    asset = {'splitBody':[
        {'type':'paragraph','crumbs':[{'content':'Harry Potter','marks':['em']}, {'content':' -tähti Rupert Grint näyttelee trillerissä Yön lapsi.'}]},
        {'type':'paragraph','crumbs':[{'content':'Yön lapsi, ensi-ilta perjantaina 6.11. elokuvateattereissa','marks':['endnote']}]},
        {'type':'paragraph','crumbs':[{'content':'Psykologinen trilleri ★★','marks':['endnote']}]},
    ]}
    assert ISScraper()._extract_movie_title(asset) == 'Yön lapsi'
