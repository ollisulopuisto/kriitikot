"""The narrow HS repair may add one verified row but never rewrite reviews."""
import importlib.util
from pathlib import Path
import sqlite3
import pytest
spec=importlib.util.spec_from_file_location('hs_restore',Path(__file__).parents[1]/'scripts/restore_verified_hs_review.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def database():
    db=sqlite3.connect(':memory:')
    db.executescript('''CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT);
    CREATE TABLE critics(id INTEGER PRIMARY KEY,name TEXT,media TEXT,created_at TEXT);
    CREATE TABLE publications(id INTEGER PRIMARY KEY,short_name TEXT);
    CREATE TABLE reviews(id INTEGER PRIMARY KEY,movie_id INTEGER,critic_id INTEGER,publication_id INTEGER,rating_stars INTEGER,review_text TEXT,source_url TEXT UNIQUE,is_published INTEGER,scraped_at TEXT,created_at TEXT);
    INSERT INTO movies VALUES(361,'You Can See Everything');
    INSERT INTO publications VALUES(1,'hs');''')
    return db


def test_dryrun_apply_and_idempotence():
    db=database()
    assert module.restore(db) is True
    assert db.execute('SELECT count(*) FROM reviews').fetchone()==(0,)
    assert module.restore(db,True) is True
    assert db.execute('SELECT movie_id,rating_stars,is_published FROM reviews').fetchone()==(361,5,1)
    before=db.execute('SELECT * FROM reviews').fetchall()
    assert module.restore(db,True) is False
    assert before==db.execute('SELECT * FROM reviews').fetchall()


def test_conflicting_url_is_not_overwritten():
    db=database();module.restore(db,True)
    db.execute('UPDATE reviews SET rating_stars=4');db.commit()
    with pytest.raises(ValueError,match='conflicts'):
        module.restore(db,True)
    assert db.execute('SELECT rating_stars FROM reviews').fetchone()==(4,)


def test_missing_film_refuses_new_identity():
    db=database();db.execute('DELETE FROM movies');db.commit()
    with pytest.raises(ValueError,match='existing film'):
        module.restore(db,True)
    assert db.execute('SELECT count(*) FROM critics').fetchone()==(0,)


def test_public_metadata_read_explicitly_uses_utf8(monkeypatch):
    original=module.FIXTURE
    class CheckedFixture:
        def read_text(self, *, encoding):
            assert encoding=='utf-8'
            return original.read_text(encoding=encoding)
    monkeypatch.setattr(module,'FIXTURE',CheckedFixture())
    assert module.restore(database()) is True
