import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('episodi_repair', Path(__file__).parents[1] / 'scripts/repair_episodi_critics.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def fixture(tmp_path):
    path = tmp_path / 'reviews.db'
    c = sqlite3.connect(path)
    c.executescript('''CREATE TABLE critics(id INTEGER PRIMARY KEY,name TEXT UNIQUE);
    CREATE TABLE publications(id INTEGER PRIMARY KEY,short_name TEXT);
    CREATE TABLE movies(id INTEGER PRIMARY KEY,title TEXT);
    CREATE TABLE reviews(id INTEGER PRIMARY KEY,movie_id INTEGER,critic_id INTEGER,publication_id INTEGER,source_url TEXT,review_text TEXT,UNIQUE(movie_id,critic_id));
    INSERT INTO critics VALUES(1,'Episodi'),(2,'Jussi Huhtala'),(3,'Jouni Vikman'),(4,'Werneri Pihlajamäki');
    INSERT INTO publications VALUES(1,'episodi');''')
    for index,row in enumerate(json.loads(repair.MANIFEST.read_text()),1):
        c.execute('INSERT INTO movies VALUES(?,?)',(index,row['title']))
        c.execute('INSERT INTO reviews VALUES(?,?,1,1,?,?)',(row['id'],index,row['source_url'],'untouched'))
    c.commit();c.close()
    return path


def test_dry_run_is_read_only(tmp_path):
    path=fixture(tmp_path);before=path.read_bytes()
    assert len(repair.repair(path))==4
    assert path.read_bytes()==before


def test_apply_reuses_critics_only_changes_four_links_and_is_idempotent(tmp_path):
    path=fixture(tmp_path);before=path.read_bytes();backup=tmp_path/'backup.db'
    assert len(repair.repair(path,backup))==4
    with sqlite3.connect(backup) as saved:
        assert saved.execute('SELECT critic_id FROM reviews ORDER BY id').fetchall()==[(1,),(1,),(1,),(1,)]
        assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    c=sqlite3.connect(path)
    assert c.execute('SELECT count(*) FROM critics').fetchone()[0]==4
    assert c.execute('SELECT distinct review_text FROM reviews').fetchall()==[('untouched',)]
    assert c.execute('SELECT critic_id FROM reviews ORDER BY id').fetchall()==[(2,),(3,),(3,),(4,)]
    assert repair.repair(path)==[]


def test_identity_change_aborts_without_writes(tmp_path):
    path=fixture(tmp_path);c=sqlite3.connect(path);c.execute("UPDATE reviews SET source_url='changed' WHERE id=928");c.commit();c.close();before=path.read_bytes()
    with pytest.raises(ValueError,match='Identity changed'):repair.repair(path,tmp_path/'backup.db')
    assert path.read_bytes()==before


def test_existing_backup_is_never_overwritten(tmp_path):
    path=fixture(tmp_path);backup=tmp_path/'backup.db';backup.write_bytes(b'keep')
    with pytest.raises(FileExistsError):repair.repair(path,backup)
    assert backup.read_bytes()==b'keep'


def test_duplicate_critic_movie_aborts(tmp_path):
    path=fixture(tmp_path);c=sqlite3.connect(path);c.execute("INSERT INTO reviews VALUES(9999,1,2,1,'other','untouched')");c.commit();c.close()
    with pytest.raises(ValueError,match='Duplicate'):repair.repair(path)


def test_missing_target_does_not_create_a_critic(tmp_path):
    path=fixture(tmp_path);c=sqlite3.connect(path);c.execute('DELETE FROM critics WHERE id=4');c.commit();c.close()
    with pytest.raises(ValueError,match='Missing existing Critic'):repair.repair(path)
