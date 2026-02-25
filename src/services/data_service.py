"""
Service layer for data retrieval and processing.
Separates business logic from Flask views.
"""

import os
import json
from datetime import datetime
from collections import OrderedDict
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy.orm import joinedload
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from models import Movie, Critic, Publication, Review as DBReview, get_session

class DataService:
    def __init__(self, engine):
        self.engine = engine

    def get_grouped_reviews(self, session) -> Tuple[OrderedDict, List[Critic], int]:
        """Hakee kaikki arvostelut ryhmiteltynä elokuvittain."""
        # Hae kaikki JULKAISTUT arvostelut EAGER LOADingilla
        reviews = session.query(DBReview).filter_by(is_published=1).options(
            joinedload(DBReview.movie),
            joinedload(DBReview.critic),
            joinedload(DBReview.publication)
        ).all()
        
        # Hae kaikki kriitikot
        critics = session.query(Critic).all()
        
        # Ryhmittele elokuvittain
        grouped = {}
        movie_latest_review = {}
        
        for review in reviews:
            movie_title = review.movie.title
            critic_name = review.critic.name
            
            if movie_title not in grouped:
                grouped[movie_title] = {}
            
            if critic_name not in grouped[movie_title]:
                grouped[movie_title][critic_name] = []
            
            grouped[movie_title][critic_name].append(review)
            
            review_date = review.published_date or review.scraped_at
            if movie_title not in movie_latest_review or review_date > movie_latest_review[movie_title]:
                movie_latest_review[movie_title] = review_date
        
        # Järjestä elokuvat uusimman arvion mukaan
        sorted_movies = sorted(
            grouped.keys(), 
            key=lambda title: movie_latest_review.get(title, datetime(1900, 1, 1)), 
            reverse=True
        )
        
        grouped_ordered = OrderedDict()
        for movie_title in sorted_movies:
            grouped_ordered[movie_title] = grouped[movie_title]
        
        return grouped_ordered, sorted(critics, key=lambda c: c.name), len(reviews)

    def get_index_data(self, critic_order_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Kokoaa kaiken datan etusivua varten."""
        session = get_session(self.engine)
        try:
            grouped_reviews, all_critics, total_reviews = self.get_grouped_reviews(session)
            
            # Kriitikoiden järjestys
            if critic_order_ids:
                critic_dict = {c.id: c for c in all_critics}
                ordered_critics = [critic_dict[cid] for cid in critic_order_ids if cid in critic_dict]
                remaining = [c for c in all_critics if c.id not in critic_order_ids]
                all_critics = ordered_critics + remaining

            # Tilastot ja metatiedot
            movie_review_counts = {title: sum(len(r) for r in cr.values()) for title, cr in grouped_reviews.items()}
            
            critic_media_map = {}
            critic_review_counts = {}
            for critic in all_critics:
                c_reviews = session.query(DBReview).filter(
                    DBReview.critic_id == critic.id,
                    DBReview.is_published == 1
                ).options(joinedload(DBReview.publication)).all()
                
                publications = sorted(list(set([r.publication.short_name.upper() for r in c_reviews if r.publication])))
                critic_media_map[critic.id] = publications
                critic_review_counts[critic.id] = len(c_reviews)

            rating_distribution = {i: session.query(DBReview).filter(DBReview.rating_stars == i).count() for i in range(1, 6)}
            
            pub_stats = {}
            for pub in session.query(Publication).all():
                count = session.query(DBReview).filter(DBReview.publication_id == pub.id).count()
                if count > 0:
                    pub_stats[pub.short_name.upper()] = count
            pub_stats = dict(sorted(pub_stats.items()))

            # Elokuvakohtaiset linkit
            movies = session.query(Movie).all()
            nytleffaan_urls = {m.title: m.nytleffaan_url for m in movies if m.nytleffaan_url}
            poster_urls = {m.title: m.poster_url for m in movies if m.poster_url}
            letterboxd_urls = {m.title: m.letterboxd_url for m in movies if m.letterboxd_url}

            # Viimeisin päivitys
            latest_update = session.query(DBReview).filter_by(is_published=1).order_by(DBReview.scraped_at.desc()).first()
            last_updated = self._format_last_updated(latest_update)

            # JSON-muoto JS:lle
            all_reviews_json = {}
            for movie_title, critics_reviews_dict in grouped_reviews.items():
                all_reviews_json[movie_title] = {
                    critic_name: [review.to_dict() for review in reviews_list]
                    for critic_name, reviews_list in critics_reviews_dict.items()
                }

            return {
                'grouped_reviews': grouped_reviews,
                'all_reviews_json': json.dumps(all_reviews_json),
                'all_critics': all_critics,
                'total_reviews': total_reviews,
                'rating_distribution': rating_distribution,
                'pub_stats': pub_stats,
                'critic_media_map': critic_media_map,
                'critic_review_counts': critic_review_counts,
                'movie_review_counts': movie_review_counts,
                'nytleffaan_urls': nytleffaan_urls,
                'poster_urls': poster_urls,
                'letterboxd_urls': letterboxd_urls,
                'last_updated': last_updated
            }
        finally:
            session.close()

    def _format_last_updated(self, latest_review: Optional[DBReview]) -> Optional[datetime]:
        if not latest_review:
            return None
        
        last_updated = latest_review.published_date or latest_review.scraped_at
        display_tz = os.environ.get('DISPLAY_TIMEZONE', 'Europe/Helsinki')
        
        if ZoneInfo is not None and last_updated is not None:
            try:
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=ZoneInfo('UTC'))
                last_updated = last_updated.astimezone(ZoneInfo(display_tz))
            except Exception:
                pass
        return last_updated

    def get_paged_movies(self, offset: int, limit: int) -> Dict[str, Any]:
        """Sivutettu haku elokuvista."""
        session = get_session(self.engine)
        try:
            # 1. Kaikki julkaistut arviot elokuvien järjestämiseen
            all_published = session.query(DBReview).filter_by(is_published=1).options(joinedload(DBReview.movie)).all()
            
            movie_latest = {}
            for r in all_published:
                m_title = r.movie.title
                r_date = r.published_date or r.scraped_at
                if m_title not in movie_latest or r_date > movie_latest[m_title]:
                    movie_latest[m_title] = r_date
            
            sorted_titles = sorted(movie_latest.keys(), key=lambda t: movie_latest.get(t, datetime(1900,1,1)), reverse=True)
            total_movies = len(sorted_titles)
            paged_titles = sorted_titles[offset:offset+limit]
            
            if not paged_titles:
                return {'grouped_reviews': OrderedDict(), 'paged_titles': [], 'total': total_movies}

            # 2. Hae arvostelut vain näille elokuville
            reviews = session.query(DBReview).filter(DBReview.is_published == 1).join(Movie).filter(
                Movie.title.in_(paged_titles)
            ).options(joinedload(DBReview.movie), joinedload(DBReview.critic), joinedload(DBReview.publication)).all()
            
            grouped = {}
            for r in reviews:
                t, c = r.movie.title, r.critic.name
                if t not in grouped: grouped[t] = {}
                if c not in grouped[t]: grouped[t][c] = []
                grouped[t][c].append(r)
                
            grouped_ordered = OrderedDict()
            for t in paged_titles:
                if t in grouped: grouped_ordered[t] = grouped[t]

            # 3. Hae metatiedot
            movies_objs = session.query(Movie).filter(Movie.title.in_(paged_titles)).all()
            meta = {
                'nytleffaan_urls': {m.title: m.nytleffaan_url for m in movies_objs if m.nytleffaan_url},
                'poster_urls': {m.title: m.poster_url for m in movies_objs if m.poster_url},
                'letterboxd_urls': {m.title: m.letterboxd_url for m in movies_objs if m.letterboxd_url},
                'movie_review_counts': {m.title: session.query(DBReview).filter_by(movie_id=m.id, is_published=1).count() for m in movies_objs}
            }

            return {
                'grouped_reviews': grouped_ordered,
                'paged_titles': paged_titles,
                'total': total_movies,
                'meta': meta,
                'all_critics': sorted(session.query(Critic).all(), key=lambda c: c.name)
            }
        finally:
            session.close()
