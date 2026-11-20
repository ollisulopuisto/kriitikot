"""Transactional checks for the approved seven-row Episodi repair."""
import importlib.util
import sqlite3
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('episodi_repair', Path(__file__).resolve().parents[1] / 'scripts' / 'repair_episodi_titles.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture_db():
    db = sqlite3.connect(':memory:')
    db.executescript('''CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT,nytleffaan_url TEXT);
        CREATE TABLE reviews(id INTEGER PRIMARY KEY,movie_id INTEGER REFERENCES movies(id),critic_id INTEGER,
        source_url TEXT UNIQUE,rating_stars INTEGER,review_text TEXT,UNIQUE(movie_id,critic_id));''')
    for old, target, title, slug in module.REPAIRS:
        db.execute('INSERT OR IGNORE INTO movies VALUES(?,?,?)',(target,title,None))
        db.execute('INSERT OR IGNORE INTO movies VALUES(?,?,?)',(old,module.ORIGINAL_TITLES[old],'https://example.invalid/headline'))
        if old == target:
            db.execute('UPDATE movies SET title=?,nytleffaan_url=? WHERE id=?',(module.ORIGINAL_TITLES[old],'https://example.invalid/headline',old))
        db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',(old,old,old,'https://www.episodi.fi/elokuvat/'+slug+'/',4,'Original text'))
    db.commit()
    return db


def test_repair_dry_run_apply_and_idempotence():
    db=fixture_db()
    assert len(module.repair(db)) == 7
    assert db.execute('SELECT count(*) FROM movies').fetchone()[0] == 11
    before=db.execute('SELECT id,critic_id,source_url,rating_stars,review_text FROM reviews ORDER BY id').fetchall()
    assert len(module.repair(db,apply=True)) == 7
    assert db.execute('SELECT count(*) FROM movies').fetchone()[0] == 7
    assert db.execute('SELECT id,critic_id,source_url,rating_stars,review_text FROM reviews ORDER BY id').fetchall() == before
    assert module.repair(db,apply=True) == []
    assert db.execute('SELECT nytleffaan_url FROM movies WHERE id=370').fetchone()[0] is None


def test_repair_conflict_rolls_back_every_change():
    db=fixture_db()
    db.execute('INSERT INTO reviews VALUES(999,362,367,\'https://example.test/conflict\',3,\'Existing\')')
    db.commit()
    before=list(db.iterdump())
    with pytest.raises(ValueError,match='Conflicting'):
        module.repair(db,apply=True)
    assert list(db.iterdump()) == before


def test_repair_aborts_if_titles_or_review_links_changed():
    for sql in ("UPDATE movies SET title='A different reviewed identity' WHERE id=370",
                "DELETE FROM reviews WHERE movie_id=370"):
        db = fixture_db()
        db.execute(sql)
        db.commit()
        before = list(db.iterdump())
        with pytest.raises(ValueError):
            module.repair(db, apply=True)
        assert list(db.iterdump()) == before
