"""One-time owner-requested HS review insert. Dry-run by default; no scraper changes."""
import argparse
import sqlite3
from datetime import datetime, timezone

URL = 'https://www.hs.fi/popkulttuuri/art-2000012401104.html'
TITLE = 'The Further Mis-Adventures of Cliff Booth'
CRITIC = 'Veli-Pekka Lehtonen'
PUBLISHED = '2026-11-26 00:00:00'  # Verified calendar date, not an inferred exact time.


def add_review(db, apply=False):
    db.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        if db.execute('SELECT title FROM movies WHERE id=374').fetchone() != (TITLE,):
            raise ValueError('Target movie identity changed')
        if db.execute('SELECT name,short_name FROM publications WHERE id=1').fetchone() != ('Helsingin Sanomat', 'hs'):
            raise ValueError('Publication identity changed')
        critics = db.execute('SELECT id FROM critics WHERE name=?', (CRITIC,)).fetchall()
        if len(critics) > 1:
            raise ValueError('Ambiguous critic identity')
        rows = db.execute('''SELECT movie_id,critic_id,publication_id,rating_stars,is_published,published_date
                             FROM reviews WHERE source_url=?''', (URL,)).fetchall()
        if rows:
            if len(rows) != 1 or not critics or rows[0] != (374, critics[0][0], 1, 4, 1, PUBLISHED):
                raise ValueError('Existing review differs from audited insert')
            db.rollback()
            return []
        if critics and db.execute('SELECT id FROM reviews WHERE movie_id=374 AND critic_id=?', critics[0]).fetchone():
            raise ValueError('Conflicting review already exists')
        plan = ['insert review'] if critics else ['insert critic', 'insert review']
        if apply:
            stamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(' ')
            critic_id = critics[0][0] if critics else db.execute(
                'INSERT INTO critics(name,media,created_at) VALUES (?,?,?)', (CRITIC, 'HS', stamp)).lastrowid
            db.execute('''INSERT INTO reviews(movie_id,critic_id,publication_id,rating_stars,review_text,
                          source_url,is_published,published_date,scraped_at,created_at)
                          VALUES (374,?,1,4,NULL,?,1,?,NULL,?)''', (critic_id, URL, PUBLISHED, stamp))
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Foreign key check failed')
            db.commit()
        else:
            db.rollback()
        return plan
    except Exception:
        db.rollback()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='reviews.db')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        print(add_review(db, args.apply))
