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

    # --- Jaetut apurit ---

    @staticmethod
    def _group_by_movie_and_critic(reviews) -> Tuple[Dict, Dict]:
        """Ryhmittele arviot: (grouped[title][critic] = [reviews], viimeisin päiväys per elokuva)."""
        grouped = {}
        latest = {}
        for review in reviews:
            title = review.movie.title
            critic = review.critic.name
            grouped.setdefault(title, {}).setdefault(critic, []).append(review)
            review_date = review.published_date or review.scraped_at
            if title not in latest or review_date > latest[title]:
                latest[title] = review_date
        return grouped, latest

    @staticmethod
    def _sort_titles_by_latest(titles, latest: Dict) -> List[str]:
        return sorted(titles, key=lambda t: latest.get(t, datetime(1900, 1, 1)), reverse=True)

    @staticmethod
    def _rating_distributions(grouped: Dict) -> Dict[str, List[int]]:
        """Arvosanajakauma [1-5 tähteä] elokuvittain."""
        distributions = {}
        for title, critics_reviews in grouped.items():
            counts = [0, 0, 0, 0, 0]
            for reviews_list in critics_reviews.values():
                for r in reviews_list:
                    if r.rating_stars and 1 <= r.rating_stars <= 5:
                        counts[r.rating_stars - 1] += 1
            distributions[title] = counts
        return distributions

    @staticmethod
    def _movie_link_maps(movies) -> Dict[str, Dict[str, str]]:
        """Maps for movie external links and posters.

        Accepts either Movie ORM objects or column-tuple query results
        (title, nytleffaan_url, poster_url, letterboxd_url).
        """
        nytleffaan = {}
        poster = {}
        letterboxd = {}
        for m in movies:
            title = getattr(m, 'title', None) if not isinstance(m, (tuple, list)) else m[0]
            nyt = getattr(m, 'nytleffaan_url', None) if not isinstance(m, (tuple, list)) else m[1]
            pst = getattr(m, 'poster_url', None) if not isinstance(m, (tuple, list)) else m[2]
            lb = getattr(m, 'letterboxd_url', None) if not isinstance(m, (tuple, list)) else m[3]

            if nyt:
                nytleffaan[title] = nyt
            if pst:
                poster[title] = pst
            if lb:
                letterboxd[title] = lb

        return {
            'nytleffaan_urls': nytleffaan,
            'poster_urls': poster,
            'letterboxd_urls': letterboxd,
        }

    @staticmethod
    def _reviews_json_dict(grouped: Dict) -> Dict:
        return {
            title: {
                critic: [r.to_dict() for r in reviews_list]
                for critic, reviews_list in critics_reviews.items()
            }
            for title, critics_reviews in grouped.items()
        }

    # --- Julkiset metodit ---

    def get_grouped_reviews(self, session) -> Tuple[OrderedDict, List[Critic], int]:
        """Hakee kaikki arvostelut ryhmiteltynä elokuvittain."""
        # Hae kaikki JULKAISTUT arvostelut EAGER LOADingilla
        reviews = session.query(DBReview).filter_by(is_published=1).options(
            joinedload(DBReview.movie),
            joinedload(DBReview.critic),
            joinedload(DBReview.publication)
        ).all()

        critics = session.query(Critic).all()

        grouped, latest = self._group_by_movie_and_critic(reviews)

        # Järjestä elokuvat uusimman arvion mukaan
        grouped_ordered = OrderedDict()
        for movie_title in self._sort_titles_by_latest(grouped.keys(), latest):
            grouped_ordered[movie_title] = grouped[movie_title]

        return grouped_ordered, sorted(critics, key=lambda c: c.name), len(reviews)

    def get_reviews_json(self) -> str:
        """Kaikki arvostelut JSON-merkkijonona (reviews.json / lazy load)."""
        session = get_session(self.engine)
        try:
            grouped_reviews, _, _ = self.get_grouped_reviews(session)
            return json.dumps(self._reviews_json_dict(grouped_reviews))
        finally:
            session.close()

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

            # The published reviews and their publication are already eager
            # loaded above. Reuse that in-memory snapshot instead of querying
            # the database multiple times:
            # - critic summaries (previously 1 query per critic)
            # - rating_distribution (previously 5 separate COUNT queries)
            # - pub_stats (previously 1 query for publications + N COUNT queries)
            # In production, this reduces database queries on the index page from 23 down to 4.
            critic_publications = {critic.id: set() for critic in all_critics}
            critic_review_counts = {critic.id: 0 for critic in all_critics}
            rating_distribution = {i: 0 for i in range(1, 6)}
            pub_counts: Dict[str, int] = {}

            for critics_reviews in grouped_reviews.values():
                for reviews_list in critics_reviews.values():
                    for review in reviews_list:
                        critic_review_counts[review.critic_id] = (
                            critic_review_counts.get(review.critic_id, 0) + 1
                        )
                        if review.publication and review.publication.short_name:
                            pub_code = review.publication.short_name.upper()
                            critic_publications.setdefault(review.critic_id, set()).add(pub_code)
                            pub_counts[pub_code] = pub_counts.get(pub_code, 0) + 1
                        if review.rating_stars and 1 <= review.rating_stars <= 5:
                            rating_distribution[review.rating_stars] += 1

            critic_media_map = {
                critic.id: sorted(critic_publications[critic.id])
                for critic in all_critics
            }
            pub_stats = dict(sorted(pub_counts.items()))

            # Elokuvakohtaiset linkit: query only the required columns instead
            # of hydrating 290+ full Movie ORM entities with unused fields.
            movie_links = session.query(
                Movie.title,
                Movie.nytleffaan_url,
                Movie.poster_url,
                Movie.letterboxd_url
            ).all()
            link_maps = self._movie_link_maps(movie_links)

            # Viimeisin päivitys:
            # Reusing the already eager-loaded published reviews in memory avoids an
            # extra unindexed SQL query (reviews table scan + temp B-tree for ORDER BY)
            # which takes ~4.5ms.
            latest_update = None
            for critics_reviews in grouped_reviews.values():
                for reviews_list in critics_reviews.values():
                    for review in reviews_list:
                        if (
                            latest_update is None
                            or (review.scraped_at and (latest_update.scraped_at is None or review.scraped_at > latest_update.scraped_at))
                        ):
                            latest_update = review
            last_updated = self._format_last_updated(latest_update)

            # Note on all_reviews_json:
            # Full reviews dataset is lazy-loaded by the client via `/reviews.json`
            # (DataService.get_reviews_json). Serializing ~2.8MB of JSON here on every
            # index page load was unused dead work (~27ms + ~3.4MB memory overhead).
            return {
                'grouped_reviews': grouped_reviews,
                'all_critics': all_critics,
                'total_reviews': total_reviews,
                'rating_distribution': rating_distribution,
                'pub_stats': pub_stats,
                'critic_media_map': critic_media_map,
                'critic_review_counts': critic_review_counts,
                'movie_review_counts': movie_review_counts,
                'movie_rating_distributions': self._rating_distributions(grouped_reviews),
                'last_updated': last_updated,
                **link_maps,
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

            sorted_titles = self._sort_titles_by_latest(movie_latest.keys(), movie_latest)
            total_movies = len(sorted_titles)
            paged_titles = sorted_titles[offset:offset+limit]

            if not paged_titles:
                return {'grouped_reviews': OrderedDict(), 'paged_titles': [], 'total': total_movies}

            # 2. Hae arvostelut vain näille elokuville
            reviews = session.query(DBReview).filter(DBReview.is_published == 1).join(Movie).filter(
                Movie.title.in_(paged_titles)
            ).options(joinedload(DBReview.movie), joinedload(DBReview.critic), joinedload(DBReview.publication)).all()

            grouped, _ = self._group_by_movie_and_critic(reviews)

            grouped_ordered = OrderedDict()
            for t in paged_titles:
                if t in grouped: grouped_ordered[t] = grouped[t]

            # 3. Hae metatiedot
            movies_objs = session.query(Movie).filter(Movie.title.in_(paged_titles)).all()

            # Compute movie review counts from already eager-loaded grouped_ordered reviews
            # to avoid N+1 queries (1 SQL COUNT query per movie).
            movie_review_counts = {
                m.title: sum(len(reviews_list) for reviews_list in grouped_ordered.get(m.title, {}).values())
                for m in movies_objs
            }

            meta = {
                **self._movie_link_maps(movies_objs),
                'movie_review_counts': movie_review_counts,
                'movie_rating_distributions': self._rating_distributions(grouped_ordered)
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
