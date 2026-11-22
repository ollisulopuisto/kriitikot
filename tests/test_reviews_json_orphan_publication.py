"""The scalar export must preserve the ORM export's missing-publication rows."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, delete, event
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from models import Base, Critic, Movie, Publication, Review
from services.data_service import DataService


@pytest.mark.parametrize('deleted_publication', [False, True])
def test_reviews_json_keeps_orphan_publication_and_matches_orm_export(deleted_publication):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            critic = Critic(name='Fixture critic')
            publication = Publication(name='Fixture publication', short_name='fixture')
            removed = Publication(name='Removed publication', short_name='removed')
            movies = [Movie(title=name) for name in ['Older valid', 'Newest orphan', 'Pending orphan']]
            session.add_all([critic, publication, removed, *movies])
            session.flush()
            missing_id = removed.id if deleted_publication else 999999
            for index, movie in enumerate(movies):
                session.add(Review(
                    movie=movie, critic=critic,
                    publication_id=publication.id if index == 0 else missing_id,
                    source_url=f'https://example.test/{index}',
                    rating_stars=4 if index == 0 else None,
                    review_text='Ääni ja kuva' if index == 1 else None,
                    is_published=0 if index == 2 else 1,
                    published_date=datetime(2026, 11, 1) if index == 0 else None,
                    scraped_at=datetime(2026, 11, 2 + index),
                ))
            session.commit()
            if deleted_publication:
                session.execute(delete(Publication).where(Publication.id == removed.id))
                session.commit()

        service = DataService(engine)
        with Session(engine) as session:
            grouped, _, total = service.get_grouped_reviews(session)
            expected = service._reviews_json_dict(grouped)
            assert total == 2
        statements = []
        event.listen(engine, 'before_cursor_execute',
                     lambda conn, cur, statement, params, ctx, many: statements.append(statement))
        actual = json.loads(service.get_reviews_json())
        assert list(actual) == ['Newest orphan', 'Older valid']
        assert actual == expected
        orphan = actual['Newest orphan']['Fixture critic'][0]
        assert orphan['source_publication'] is None
        assert orphan['publication_short'] is None
        assert orphan['review_text'] == 'Ääni ja kuva'
        assert orphan['published_date'] is None
        assert len(statements) == 1, 'Keep the scalar export to a single query'
        assert 'LEFT OUTER JOIN publications' in statements[0]
    finally:
        engine.dispose()
