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
    assert data['pub_stats'] == {'TEST': 40}
    assert data['rating_distribution'] == {1: 0, 2: 0, 3: 0, 4: 40, 5: 0}
    # Exactly 3 queries:
    # 1. published reviews with joinedload (movie, critic, publication)
    # 2. all critics
    # 3. all movies for link_maps
    # (latest review for last_updated is determined in memory from published reviews)
    assert len(queries) == 3, f"Expected 3 queries, got {len(queries)}"


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
    # Pending reviews are excluded from pub_stats and rating_distribution
    assert data['pub_stats'] == {'A': 1}


def test_paged_movies_queries_do_not_grow_with_page_size():
    """get_paged_movies should not execute N+1 count queries for each movie on the page."""
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        publication = Publication(name='Test publication', short_name='test')
        critic = Critic(name='Test critic')
        session.add_all([publication, critic])
        for i in range(25):
            movie = Movie(title=f'Movie {i:02d}')
            session.add(movie)
            session.add(Review(movie=movie, critic=critic, publication=publication,
                               source_url=f'https://example.test/m{i}', rating_stars=4,
                               is_published=1, scraped_at=datetime(2026, 10, 29)))
        session.commit()

    queries = []
    event.listen(engine, 'before_cursor_execute', lambda conn, cur, statement, params, ctx, many: queries.append(statement))
    data = DataService(engine).get_paged_movies(offset=0, limit=20)

    assert len(data['paged_titles']) == 20
    assert all(count == 1 for count in data['meta']['movie_review_counts'].values())
    # Exactly 4 queries:
    # 1. aggregated movie title ordering query
    # 2. reviews joined for paged movies
    # 3. movies objects for paged movies metadata
    # 4. all critics for table headers
    assert len(queries) == 4, f"Expected 4 queries, got {len(queries)}"


def test_paged_movies_ordering_and_pagination():
    """Verify get_paged_movies orders by latest review, slices accurately, and excludes unreviewed/unpublished."""
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        pub = Publication(name='Pub', short_name='p')
        c1 = Critic(name='Critic 1')
        session.add_all([pub, c1])
        m_old = Movie(title='Movie Old')
        m_mid = Movie(title='Movie Mid')
        m_new = Movie(title='Movie New')
        m_unpub = Movie(title='Movie Unpub')
        m_empty = Movie(title='Movie No Reviews')
        session.add_all([m_old, m_mid, m_new, m_unpub, m_empty])
        session.flush()

        session.add_all([
            Review(movie=m_old, critic=c1, publication=pub, source_url='http://old', is_published=1,
                   published_date=datetime(2025, 1, 1), scraped_at=datetime(2025, 1, 1)),
            Review(movie=m_mid, critic=c1, publication=pub, source_url='http://mid', is_published=1,
                   published_date=datetime(2025, 6, 1), scraped_at=datetime(2025, 6, 1)),
            Review(movie=m_new, critic=c1, publication=pub, source_url='http://new', is_published=1,
                   published_date=datetime(2026, 1, 1), scraped_at=datetime(2026, 1, 1)),
            Review(movie=m_unpub, critic=c1, publication=pub, source_url='http://unpub', is_published=0,
                   published_date=datetime(2026, 12, 1), scraped_at=datetime(2026, 12, 1)),
        ])
        session.commit()

    ds = DataService(engine)

    # Page 1 (limit 2)
    p1 = ds.get_paged_movies(offset=0, limit=2)
    assert p1['total'] == 3
    assert p1['paged_titles'] == ['Movie New', 'Movie Mid']
    assert list(p1['grouped_reviews'].keys()) == ['Movie New', 'Movie Mid']

    # Page 2 (limit 2)
    p2 = ds.get_paged_movies(offset=2, limit=2)
    assert p2['total'] == 3
    assert p2['paged_titles'] == ['Movie Old']
    assert list(p2['grouped_reviews'].keys()) == ['Movie Old']

    # Page 3 (past end)
    p3 = ds.get_paged_movies(offset=4, limit=2)
    assert p3['total'] == 3
    assert p3['paged_titles'] == []
    assert len(p3['grouped_reviews']) == 0


def test_paged_movies_tiebreak_on_identical_timestamp():
    """Verify movies with identical timestamps are deterministically sorted by title."""
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        pub = Publication(name='Pub', short_name='p')
        c1 = Critic(name='Critic 1')
        session.add_all([pub, c1])
        m_z = Movie(title='Movie Z')
        m_a = Movie(title='Movie A')
        session.add_all([m_z, m_a])
        session.flush()

        shared_time = datetime(2026, 3, 15, 12, 0, 0)
        session.add_all([
            Review(movie=m_z, critic=c1, publication=pub, source_url='http://z', is_published=1,
                   published_date=shared_time, scraped_at=shared_time),
            Review(movie=m_a, critic=c1, publication=pub, source_url='http://a', is_published=1,
                   published_date=shared_time, scraped_at=shared_time),
        ])
        session.commit()

    ds = DataService(engine)
    paged = ds.get_paged_movies(offset=0, limit=10)
    assert paged['paged_titles'] == ['Movie A', 'Movie Z']
    assert paged['total'] == 2
