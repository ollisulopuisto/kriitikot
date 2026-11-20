"""Repair seven reviewed Episodi headline rows, preserving every review.

Dry run by default. Run only after the extraction fix is merged. The mapping
was approved on 20 November 2026; this is not a general title normalizer.
"""
import argparse
import sqlite3

REPAIRS = (
    (365, 361, 'You Can See Everything', 'you-can-see-everything'),
    (367, 362, 'Punaista lunta', 'punaista-lunta'),
    (368, 364, 'Paper Tiger', 'paper-tiger'),
    (369, 369, 'The Magic Faraway Tree', 'the-magic-faraway-tree'),
    (370, 370, 'Katti hatussa', 'katti-hatussa'),
    (371, 371, 'Dry Leaf', 'dry-leaf'),
    (372, 363, 'La bola negra', 'la-bola-negra'),
)


ORIGINAL_TITLES = {372: 'Federico García Lorcan keskeneräinen teos innoitti viiden tähden elokuvan Espanjan sisällissodasta', 371: 'Dry Leaf on keskittymistä vaativa anti-TikTok-elokuva', 370: 'Audrey Geisel kielsi aviomiehensä kirjojen näytellyt versiot', 369: 'Viisikko-kirjoista tunnetun Enid Blytonin vähemmän tuttu The Magic Faraway Tree herää eloon', 368: 'Miles Teller, Adam Driver ja Scarlett Johansson tähdittävät James Grayn trilleriä Paper Tiger', 367: 'Käsikirjoittajana tunnetun Ilja Rautsin esikoispitkä Punaista lunta haastaa Kuutamosonaatin aseman', 365: 'Viiden tähden You Can See Everything on kuin taikatemppu'}

def repair(connection, apply=False):
    columns = [r[1] for r in connection.execute('PRAGMA table_info(reviews)')]
    mid = columns.index('movie_id')
    review_ids = set()
    changes = []
    connection.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        before = connection.execute('SELECT * FROM reviews ORDER BY id').fetchall()
        for old, target, title, slug in REPAIRS:
            url = f'https://www.episodi.fi/elokuvat/{slug}/'
            rows = connection.execute('SELECT id, movie_id, critic_id FROM reviews WHERE source_url=?', (url,)).fetchall()
            if len(rows) != 1:
                raise ValueError(f'Expected one review for {url}, got {len(rows)}')
            rid, current, critic = rows[0]
            review_ids.add(rid)
            if current not in (old, target):
                raise ValueError(f'Review {rid} has unexpected movie {current}')
            movie = connection.execute('SELECT title FROM movies WHERE id=?', (target,)).fetchone()
            if not movie or (old != target and movie[0] != title):
                raise ValueError(f'Target {target} does not match reviewed identity')
            original = connection.execute('SELECT title FROM movies WHERE id=?', (old,)).fetchone()
            if current == old and original and original[0] not in (ORIGINAL_TITLES[old], title):
                raise ValueError(f'Movie {old} title changed since audit')
            if old != target:
                if current == target:
                    continue
                others = connection.execute('SELECT id FROM reviews WHERE movie_id=? AND id!=?', (old, rid)).fetchall()
                if others:
                    raise ValueError(f'Movie {old} has additional unreviewed reviews')
                duplicate = connection.execute('SELECT id FROM reviews WHERE movie_id=? AND critic_id=?', (target, critic)).fetchone()
                if duplicate:
                    raise ValueError(f'Conflicting critic/movie review {duplicate[0]}')
                changes.append((rid, old, target, title))
                if apply:
                    connection.execute('UPDATE reviews SET movie_id=? WHERE id=?', (target, rid))
                    connection.execute('DELETE FROM movies WHERE id=?', (old,))
            elif movie[0] != title:
                changes.append((rid, old, target, title))
                if apply:
                    # These URLs were generated from corrupt headlines. Remove
                    # them rather than inventing destination links.
                    connection.execute('UPDATE movies SET title=?, nytleffaan_url=NULL WHERE id=?', (title, old))
        after = connection.execute('SELECT * FROM reviews ORDER BY id').fetchall()
        strip_movie = lambda rows: [tuple(v for i, v in enumerate(row) if i != mid) for row in rows]
        if strip_movie(before) != strip_movie(after):
            raise ValueError('Review content or review count changed')
        if len(review_ids) != 7:
            raise ValueError('Expected seven distinct source reviews')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key integrity check failed')
        if apply:
            connection.commit()
        else:
            connection.rollback()
        return changes
    except Exception:
        connection.rollback()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='reviews.db')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        for row in repair(db, args.apply):
            print(row)
    print('Applied' if args.apply else 'Dry run only')
