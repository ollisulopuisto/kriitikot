#!/usr/bin/env python3
"""Normalize critic names across all publications.

This script will:
- For each Publication in the DB, build normalization patterns using
  the publication short_name and full name.
- For each Critic referenced by reviews in that publication, normalize
  the critic.name by removing trailing publication markers (e.g., " HS",
  " Helsingin Sanomat", " Iltalehti", etc.).
- If a Critic row already exists with the normalized name, reassign
  reviews and delete duplicates (same movie+critic+publication).
- Otherwise rename the Critic row.

NOTE: You should run the backups script or commit DB backups before using this.
"""
import sys
sys.path.insert(0, '/workspaces/kriitikot/src')
from models import get_session, Critic, Publication, Review
from scrapers.hs import HSScraper
from sqlalchemy import and_
import re


def normalize_name_for_publication(name: str, pub: Publication):
    if not name or not isinstance(name, str):
        return name

    # Prepare patterns: short_name (e.g., 'hs') and full name (e.g., 'Helsingin Sanomat')
    short = (pub.short_name or '').strip()
    full = (pub.name or '').strip()

    # Escape for regex, allow optional comma/space before suffix, case-insensitive
    parts = []
    if short:
        parts.append(re.escape(short))
        parts.append(re.escape(short.upper()))
    if full:
        parts.append(re.escape(full))

    if not parts:
        return name.strip()

    pattern = r"\s*(?:,)?\s*(?:" + '|'.join(parts) + r")\s*$"
    new = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
    return new if new else name.strip()


def main():
    session = get_session()
    pubs = session.query(Publication).all()
    if not pubs:
        print('No publications found; aborting')
        return

    for pub in pubs:
        print(f'Processing publication: {pub.short_name} ({pub.name})')
        reviews = session.query(Review).filter(Review.publication_id == pub.id).all()
        critic_ids = sorted({r.critic_id for r in reviews})
        print(f'  Found {len(critic_ids)} distinct critics for {pub.short_name}')

        for cid in critic_ids:
            critic = session.get(Critic, cid)
            if not critic:
                continue
            orig = critic.name
            norm = normalize_name_for_publication(orig, pub)
            if norm == orig:
                continue

            print(f'  Normalizing critic id={cid}: "{orig}" -> "{norm}"')

            existing = session.query(Critic).filter(Critic.name == norm).first()
            if existing:
                print(f'    Found existing critic id={existing.id} with normalized name; reassigning reviews')
                # Reassign reviews in this publication
                pub_reviews = session.query(Review).filter(and_(Review.critic_id == critic.id, Review.publication_id == pub.id)).all()
                for r in pub_reviews:
                    dup = session.query(Review).filter(and_(Review.movie_id == r.movie_id, Review.critic_id == existing.id, Review.publication_id == pub.id)).first()
                    if dup:
                        print(f'      Duplicate detected for movie_id={r.movie_id}; deleting review id={r.id}')
                        session.delete(r)
                    else:
                        print(f'      Reassigning review id={r.id} -> critic_id={existing.id}')
                        r.critic_id = existing.id
                session.commit()

                # If old critic has no reviews at all now, delete
                rem = session.query(Review).filter(Review.critic_id == critic.id).first()
                if not rem:
                    print(f'      Deleting old critic id={critic.id} "{orig}"')
                    session.delete(critic)
                    session.commit()
            else:
                # Try renaming
                print(f'    Renaming critic id={critic.id} to "{norm}"')
                critic.name = norm
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f'    ERROR renaming critic id={critic.id}: {e} -- skipping')

    print('All publications processed.')


if __name__ == '__main__':
    main()
