#!/usr/bin/env python3
"""Normalize critic names for Helsingin Sanomat reviews in the DB.

This script uses the same normalization logic as the HS scraper to remove
trailing publication markers ("HS", "Helsingin Sanomat"). It will:

- For each Critic referenced by HS reviews, compute normalized name.
- If a Critic with the normalized name already exists, reassign HS reviews
  to that Critic (deleting any exact-duplicate reviews that would violate
  the unique constraint).
- Otherwise, rename the Critic to the normalized name.

Run from repository root:
    python3 scripts/normalize_hs_critics.py
"""
import sys
sys.path.insert(0, '/workspaces/kriitikot/src')
from models import get_session, Critic, Publication, Review
from scrapers.hs import HSScraper
from sqlalchemy import and_


def main():
    session = get_session()
    pub = session.query(Publication).filter_by(short_name='hs').first()
    if not pub:
        print('Publication "hs" not found in DB; aborting.')
        return

    hs = HSScraper()

    # Collect critics that have HS reviews
    hs_reviews = session.query(Review).filter(Review.publication_id == pub.id).all()
    if not hs_reviews:
        print('No HS reviews found. Nothing to do.')
        return

    critic_ids = sorted({r.critic_id for r in hs_reviews})
    print(f'Found {len(critic_ids)} distinct critics referenced by HS reviews')

    for cid in critic_ids:
        critic = session.query(Critic).get(cid)
        if not critic:
            continue
        orig_name = critic.name
        norm = hs._normalize_critic_name(orig_name)
        if norm == orig_name:
            continue

        print(f'Normalizing Critic id={cid}: "{orig_name}" -> "{norm}"')

        # Is there already a critic with the normalized name?
        existing = session.query(Critic).filter(Critic.name == norm).first()

        if existing:
            print(f'  Found existing critic id={existing.id} with normalized name; reassigning reviews')
            # Reassign reviews from critic -> existing, taking care of duplicates
            reviews = session.query(Review).filter(and_(Review.critic_id == critic.id, Review.publication_id == pub.id)).all()
            for r in reviews:
                dup = session.query(Review).filter(and_(Review.movie_id == r.movie_id, Review.critic_id == existing.id, Review.publication_id == pub.id)).first()
                if dup:
                    # Duplicate would be created: delete the current review (r)
                    print(f'    Duplicate detected for movie_id={r.movie_id}; deleting review id={r.id}')
                    session.delete(r)
                else:
                    print(f'    Reassigning review id={r.id} -> critic_id={existing.id}')
                    r.critic_id = existing.id

            session.commit()

            # If old critic has no more reviews, delete it
            remaining = session.query(Review).filter(Review.critic_id == critic.id).first()
            if not remaining:
                print(f'    Deleting old critic id={critic.id} "{orig_name}"')
                session.delete(critic)
                session.commit()

        else:
            # Rename the critic row to normalized name
            print(f'  Renaming critic id={critic.id} to "{norm}"')
            critic.name = norm
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print(f'  ERROR renaming critic id={critic.id}: {e} -- skipping')

    print('Normalization complete')


if __name__ == '__main__':
    main()
