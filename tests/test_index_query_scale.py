"""The index already loads published reviews; critic summaries must reuse them."""
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from models import Base, Movie, Critic, Publication, Review
from services.data_service import DataService


def test_index_critic_queries_do_not_grow_with_critic_count():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        movie = Movie(title='Scale movie')
        publication = Publication(name='Test publication', short_name='test')
        session.add_all([movie, publication])
        for i in range(40):
            critic = Critic(name=f'Critic {i}')
            session.add(critic)
            session.add(Review(movie=movie, critic=critic, publication=publication,
                               source_url=f'https://example.test/{i}', rating_stars=4,
                               is_published=1, scraped_at=datetime(2026, 10, 29)))
        session.commit()
    queries = []
    event.listen(engine, 'before_cursor_execute', lambda conn, cur, statement, params, ctx, many: queries.append(statement))
    data = DataService(engine).get_index_data()
    assert data['total_reviews'] == 40
    assert all(value == ['TEST'] for value in data['critic_media_map'].values())
    assert all(value == 1 for value in data['critic_review_counts'].values())
    assert len(queries) == 11, len(queries)


def test_critic_summaries_keep_zero_critics_and_exclude_pending_reviews():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        movie = Movie(title='Published')
        pending_movie = Movie(title='Pending')
        c1, c2 = Critic(name='Active'), Critic(name='No reviews')
        p1 = Publication(name='A pub', short_name='a')
        p2 = Publication(name='B pub', short_name='b')
        session.add_all([movie, pending_movie, c1, c2, p1, p2])
        session.flush()
        session.add_all([
            Review(movie=movie, critic=c1, publication=p1, source_url='https://example.test/a', is_published=1),
            Review(movie=pending_movie, critic=c1, publication=p2, source_url='https://example.test/b', is_published=0),
        ])
        session.commit()
        active, empty = c1.id, c2.id
    data = DataService(engine).get_index_data()
    assert data['critic_media_map'] == {active: ['A'], empty: []}
    assert data['critic_review_counts'] == {active: 1, empty: 0}
