#!/usr/bin/env python3
"""
Poista testidata tietokannasta.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models import get_session, Movie, Critic, Review as DBReview

session = get_session()

try:
    # Poista testielokuvat
    test_movies = session.query(Movie).filter(
        Movie.title.in_(['Testielokuva 1', 'Testielokuva 2'])
    ).all()
    
    for movie in test_movies:
        # Poista ensin kaikki arvostelut
        reviews = session.query(DBReview).filter_by(movie_id=movie.id).all()
        for review in reviews:
            session.delete(review)
        session.delete(movie)
        print(f"🗑️  Poistettu elokuva: {movie.title}")
    
    # Poista testikriitikot
    test_critics = session.query(Critic).filter(
        Critic.name.in_(['Matti Meikäläinen', 'Anna Asiantuntija', 'Pekka Pohdiskelija'])
    ).all()
    
    for critic in test_critics:
        # Poista ensin kaikki arvostelut
        reviews = session.query(DBReview).filter_by(critic_id=critic.id).all()
        for review in reviews:
            session.delete(review)
        session.delete(critic)
        print(f"🗑️  Poistettu kriitikko: {critic.name}")
    
    session.commit()
    
    print("\n✅ Testidata poistettu!")
    print("\n📊 Tietokannan tila:")
    print(f"  - Elokuvia: {session.query(Movie).count()}")
    print(f"  - Kriitikoita: {session.query(Critic).count()}")
    print(f"  - Arvosteluja: {session.query(DBReview).count()}")
    
except Exception as e:
    print(f"❌ Virhe: {e}")
    session.rollback()
    raise

finally:
    session.close()
