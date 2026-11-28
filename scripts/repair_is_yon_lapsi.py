"""Correct one audited IS review link. Dry-run by default, no network/deletions."""
import argparse
import sqlite3

URL = 'https://www.is.fi/tv-ja-elokuvat/art-2000012358997.html'


def repair(connection, apply=False):
    connection.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        row = connection.execute('''SELECT r.id,r.movie_id,r.critic_id,r.review_text,p.short_name
            FROM reviews r JOIN publications p ON p.id=r.publication_id WHERE r.source_url=?''', (URL,)).fetchone()
        if not row or row[0] != 1087 or row[4] != 'is' or 'Yön lapsi, ensi-ilta' not in (row[3] or ''):
            raise ValueError('Audited source identity changed')
        target = connection.execute('SELECT title FROM movies WHERE id=348').fetchone()
        if target != ('Yön Lapsi',):
            raise ValueError('Target film identity changed')
        if row[1] == 348:
            connection.rollback()
            return []
        old = connection.execute('SELECT title FROM movies WHERE id=351').fetchone()
        if row[1] != 351 or old != ('Harry Potter',):
            raise ValueError('Original film identity changed')
        if connection.execute('SELECT id FROM reviews WHERE movie_id=348 AND critic_id=?', (row[2],)).fetchone():
            raise ValueError('Conflicting critic review')
        if apply:
            connection.execute('UPDATE reviews SET movie_id=348 WHERE id=1087 AND movie_id=351')
            if connection.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Foreign key check failed')
            connection.commit()
        else:
            connection.rollback()
        return [(1087, 351, 348)]
    except Exception:
        connection.rollback()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='reviews.db')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        print(repair(db, args.apply))
