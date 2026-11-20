"""Restore one independently verified public HS preview. Dry run by default.

Source: https://www.hs.fi/popkulttuuri/art-2000012404132.html
Public metadata captured 2026-11-20. No subscriber article text is imported.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from scrapers.hs import HSScraper

URL='https://www.hs.fi/popkulttuuri/art-2000012404132.html'
TITLE='You Can See Everything'
AUTHOR='Tero Kartastenpää'
FIXTURE=Path(__file__).resolve().parents[1]/'tests/test_data/hs_you_can_public_metadata.json'


def restore(db,apply=False):
    asset=json.loads(FIXTURE.read_text(encoding='utf-8'))
    parser=HSScraper()
    author=parser._normalize_critic_name(asset['byLine'])
    rating=parser._extract_rating(asset)
    if (asset['id']!=2000012404132 or asset['shareUrl']!=URL or
        TITLE not in asset['metaTitle'] or TITLE not in asset['ingress'] or
        author!=AUTHOR or rating!=5):
        raise ValueError('Public source metadata no longer matches verified review')
    db.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        before=db.execute('SELECT * FROM reviews ORDER BY id').fetchall()
        movie=db.execute('SELECT id FROM movies WHERE title=?',(TITLE,)).fetchall()
        publication=db.execute('SELECT id FROM publications WHERE short_name=?',('hs',)).fetchall()
        if len(movie)!=1 or len(publication)!=1:
            raise ValueError('Expected exact existing film and HS publication')
        critics=db.execute('SELECT id FROM critics WHERE name=?',(AUTHOR,)).fetchall()
        if len(critics)>1:
            raise ValueError('Ambiguous critic identity')
        existing=db.execute('SELECT movie_id,critic_id,publication_id,rating_stars,is_published FROM reviews WHERE source_url=?',(URL,)).fetchone()
        if existing:
            if not critics or existing!=(movie[0][0],critics[0][0],publication[0][0],5,1):
                raise ValueError('Existing source URL conflicts with verified metadata')
            db.rollback()
            return False
        if critics and db.execute('SELECT id FROM reviews WHERE movie_id=? AND critic_id=?',(movie[0][0],critics[0][0])).fetchone():
            raise ValueError('Existing film/critic review needs manual reconciliation')
        if not apply:
            db.rollback()
            return True
        if not critics:
            cid=db.execute("INSERT INTO critics(name,media,created_at) VALUES (?, 'HS', CURRENT_TIMESTAMP)",(AUTHOR,)).lastrowid
        else:
            cid=critics[0][0]
        rid=db.execute('INSERT INTO reviews(movie_id,critic_id,publication_id,rating_stars,review_text,source_url,is_published,scraped_at,created_at) VALUES (?,?,?,?,?,?,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)',(movie[0][0],cid,publication[0][0],rating,asset['ingress'],URL)).lastrowid
        after=db.execute('SELECT * FROM reviews WHERE id!=? ORDER BY id',(rid,)).fetchall()
        if before!=after or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Existing review data or foreign keys changed')
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


if __name__=='__main__':
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--database',default='reviews.db')
    args.add_argument('--apply',action='store_true')
    options=args.parse_args()
    with sqlite3.connect(options.database) as connection:
        changed=restore(connection,options.apply)
    print('Added verified HS review' if changed and options.apply else 'Would add verified HS review' if changed else 'Already restored')
