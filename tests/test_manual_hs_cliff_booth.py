import importlib.util
import sqlite3
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('manual_hs', Path(__file__).parents[1] / 'scripts/add_manual_hs_cliff_booth.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def db():
    connection = sqlite3.connect(':memory:')
    connection.executescript('''
      CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT);
      CREATE TABLE publications(id INTEGER PRIMARY KEY,name TEXT,short_name TEXT);
      CREATE TABLE critics(id INTEGER PRIMARY KEY,name TEXT,media TEXT,created_at TEXT);
      CREATE TABLE reviews(id INTEGER PRIMARY KEY,movie_id INTEGER REFERENCES movies(id),
        critic_id INTEGER REFERENCES critics(id),publication_id INTEGER REFERENCES publications(id),
        rating_stars INTEGER,review_text TEXT,source_url TEXT UNIQUE,is_published INTEGER,
        published_date TEXT,scraped_at TEXT,created_at TEXT);
    ''')
    connection.execute('INSERT INTO movies VALUES(374,?)', (module.TITLE,))
    connection.execute("INSERT INTO publications VALUES(1,'Helsingin Sanomat','hs')")
    connection.commit()
    yield connection
    connection.close()


def test_dry_run_apply_idempotent_and_existing_data_unchanged(db):
    before = list(db.iterdump())
    assert module.add_review(db) == ['insert critic', 'insert review']
    assert list(db.iterdump()) == before
    assert module.add_review(db, True) == ['insert critic', 'insert review']
    assert db.execute('SELECT name,media FROM critics').fetchall() == [(module.CRITIC, 'HS')]
    assert db.execute('SELECT movie_id,rating_stars,source_url,is_published,published_date,review_text,scraped_at FROM reviews').fetchall() == [
        (374, 4, module.URL, 1, module.PUBLISHED, None, None)]
    after = list(db.iterdump())
    assert module.add_review(db, True) == []
    assert list(db.iterdump()) == after
    assert not db.execute('PRAGMA foreign_key_check').fetchall()


def test_existing_critic_reused(db):
    db.execute('INSERT INTO critics(id,name) VALUES(23,?)', (module.CRITIC,))
    db.commit()
    assert module.add_review(db, True) == ['insert review']
    assert db.execute('SELECT critic_id FROM reviews').fetchone() == (23,)


@pytest.mark.parametrize('change', ['movie','publication','duplicate_critic','wrong_review','conflict'])
def test_identity_or_conflict_aborts_without_changes(db, change):
    if change == 'movie':
        db.execute("UPDATE movies SET title='Wrong'")
    elif change == 'publication':
        db.execute("UPDATE publications SET short_name='wrong'")
    else:
        db.execute('INSERT INTO critics(id,name) VALUES(23,?)', (module.CRITIC,))
        if change == 'duplicate_critic':
            db.execute('INSERT INTO critics(id,name) VALUES(24,?)', (module.CRITIC,))
        else:
            url = module.URL if change == 'wrong_review' else 'https://example.invalid/other'
            db.execute('INSERT INTO reviews(movie_id,critic_id,publication_id,rating_stars,source_url) VALUES(374,23,1,2,?)', (url,))
    db.commit()
    before = list(db.iterdump())
    with pytest.raises(ValueError):
        module.add_review(db, True)
    assert list(db.iterdump()) == before
