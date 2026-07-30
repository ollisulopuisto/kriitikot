"""
Elokuvien yhdistäminen.

Jaettu logiikka admin-näkymälle (src/app.py) ja eräajoskriptille
(scripts/merge_duplicates.py), jotta molemmat käsittelevät samat reunatapaukset:
kriitikkotörmäykset ja metatietojen siirto.
"""

from typing import List, NamedTuple, Optional

from models import Movie, Review


# Metatietokentät jotka siirretään duplikaatilta kanoniselle jos puuttuvat
METADATA_FIELDS = ('tmdb_id', 'imdb_id', 'poster_url', 'letterboxd_url', 'nytleffaan_url')


class MergeResult(NamedTuple):
    """Yhdistämisen tulos."""
    moved: int                  # siirrettyjen arvostelujen määrä
    dropped: int                # poistettujen (törmäävien) arvostelujen määrä
    carried_metadata: List[str]  # kanoniselle siirretyt metatietokentät
    canonical_title: str
    duplicate_title: str


def merge_movies(session, canonical_id: int, duplicate_id: int) -> Optional[MergeResult]:
    """Yhdistä duplicate_id kanoniseen elokuvaan canonical_id.

    Siirtää arvostelut kanoniselle elokuvalle. Jos kanonisella on jo arvostelu
    samalta kriitikolta, duplikaatin arvostelu poistetaan — muuten
    UniqueConstraint('movie_id', 'critic_id') kaataisi tallennuksen.

    Täydentää kanonisen elokuvan puuttuvat metatiedot duplikaatilta ennen
    duplikaatin poistoa.

    Kutsuja vastaa committaamisesta.

    Returns:
        MergeResult, tai None jos jompaakumpaa elokuvaa ei löydy.
    """
    canonical = session.get(Movie, canonical_id)
    duplicate = session.get(Movie, duplicate_id)

    if not canonical or not duplicate:
        return None

    canonical_title = canonical.title
    duplicate_title = duplicate.title

    # 1. Siirrä arvostelut, pudota kriitikkotörmäykset
    moved = 0
    dropped = 0
    for review in session.query(Review).filter_by(movie_id=duplicate_id).all():
        collision = session.query(Review).filter_by(
            movie_id=canonical_id,
            critic_id=review.critic_id
        ).first()

        if collision:
            session.delete(review)
            dropped += 1
        else:
            review.movie = canonical
            moved += 1

    # 2. Täydennä puuttuvat metatiedot duplikaatilta
    carried_metadata = []
    for field in METADATA_FIELDS:
        if not getattr(canonical, field) and getattr(duplicate, field):
            setattr(canonical, field, getattr(duplicate, field))
            carried_metadata.append(field)

    # 3. Poista duplikaatti
    session.delete(duplicate)

    return MergeResult(
        moved=moved,
        dropped=dropped,
        carried_metadata=carried_metadata,
        canonical_title=canonical_title,
        duplicate_title=duplicate_title,
    )
