#!/usr/bin/env python3
"""Four source-verified Episodi critic links. Dry-run by default; no network."""
import argparse
import json
import sqlite3
from pathlib import Path

MANIFEST = Path(__file__).with_name('repairs') / 'episodi-critics-2026-11-25.json'


def plan(connection):
    changes = []
    for row in json.loads(MANIFEST.read_text()):
        current = connection.execute(
            'SELECT r.critic_id,c.name,p.short_name,r.source_url,m.title,r.movie_id '
            'FROM reviews r JOIN critics c ON c.id=r.critic_id '
            'JOIN publications p ON p.id=r.publication_id '
            'JOIN movies m ON m.id=r.movie_id WHERE r.id=?', (row['id'],)
        ).fetchone()
        if not current or current[2:5] != ('episodi', row['source_url'], row['title']):
            raise ValueError(f"Identity changed for review {row['id']}")
        target = connection.execute('SELECT id FROM critics WHERE name=?', (row['new_critic'],)).fetchone()
        if not target:
            raise ValueError(f"Missing existing Critic: {row['new_critic']}")
        if current[0] == target[0]:
            continue
        if current[1] != row['critic']:
            raise ValueError(f"Unexpected current critic for review {row['id']}")
        conflict = connection.execute('SELECT id FROM reviews WHERE movie_id=? AND critic_id=? AND id<>?',
                                      (current[5], target[0], row['id'])).fetchone()
        if conflict:
            raise ValueError(f"Duplicate movie/critic would result for review {row['id']}")
        changes.append({**row, 'old_critic_id': current[0], 'new_critic_id': target[0]})
    return changes


def repair(database, backup=None):
    database = Path(database).resolve(strict=True)
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as read:
        preview = plan(read)
    if backup is None or not preview:
        return preview
    backup = Path(backup).resolve()
    if backup == database:
        raise ValueError('Backup must not be the source database')
    # Exclusive creation, never overwrite an earlier backup.
    with backup.open('xb'):
        pass
    with sqlite3.connect(database.as_uri() + '?mode=rw', uri=True) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN IMMEDIATE')
        changes = plan(connection)
        if changes != preview:
            raise ValueError('Database changed since dry-run')
        # A second read connection snapshots the committed DB while this
        # connection holds the writer lock. Only then are rows changed.
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as source:
            with sqlite3.connect(backup) as destination:
                source.backup(destination)
        if not backup.stat().st_size:
            raise ValueError('Backup is empty')
        for row in changes:
            cursor = connection.execute('UPDATE reviews SET critic_id=? WHERE id=? AND critic_id=?',
                                        (row['new_critic_id'], row['id'], row['old_critic_id']))
            if cursor.rowcount != 1:
                raise ValueError('Concurrent review change')
        violations = connection.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise ValueError('Foreign key check failed')
        connection.commit()
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', help='New backup path, required with --apply')
    args = parser.parse_args()
    if args.apply != bool(args.backup):
        parser.error('--apply and --backup must be used together')
    print(json.dumps(repair(args.database, args.backup), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
