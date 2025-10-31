#!/usr/bin/env python3
"""
Testidatan lisääminen tietokantaan multi-media-testaamista varten.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models import get_session, Movie, Critic, Publication, Review as DBReview

session = get_session()

try:
    # Hae julkaisut
    hs = session.query(Publication).filter_by(short_name='hs').first()
    ts = session.query(Publication).filter_by(short_name='ts').first()
    ksml = session.query(Publication).filter_by(short_name='ksml').first()
    
    # Luo testielokuvat
    movie1 = Movie(title="Testielokuva 1")
    movie2 = Movie(title="Testielokuva 2")
    session.add_all([movie1, movie2])
    session.flush()
    
    # Luo kriitikko joka kirjoittaa MOLEMPIIN medioihin (HS ja TS)
    critic_multi = Critic(name="Matti Meikäläinen")  # Ei media-kenttää!
    session.add(critic_multi)
    session.flush()
    
    # Luo muita kriitikkoja
    critic_hs = Critic(name="Anna Asiantuntija")
    critic_ksml = Critic(name="Pekka Pohdiskelija")
    session.add_all([critic_hs, critic_ksml])
    session.flush()
    
    # TESTI: Matti kirjoittaa samasta elokuvasta HS:ään JA TS:ään
    review1_hs = DBReview(
        movie_id=movie1.id,
        critic_id=critic_multi.id,
        publication_id=hs.id,
        rating_stars=4,
        review_text="Hieno elokuva! (HS-arvostelu)",
        source_url="https://hs.fi/test1"
    )
    
    review1_ts = DBReview(
        movie_id=movie1.id,
        critic_id=critic_multi.id,
        publication_id=ts.id,
        rating_stars=5,
        review_text="Erinomainen! (TS-arvostelu)",
        source_url="https://ts.fi/test1"
    )
    
    # Anna kirjoittaa vain HS:ään
    review2_hs = DBReview(
        movie_id=movie1.id,
        critic_id=critic_hs.id,
        publication_id=hs.id,
        rating_stars=3,
        review_text="Ihan ok elokuva.",
        source_url="https://hs.fi/test2"
    )
    
    # Pekka kirjoittaa KSML:ään
    review3_ksml = DBReview(
        movie_id=movie2.id,
        critic_id=critic_ksml.id,
        publication_id=ksml.id,
        rating_stars=5,
        review_text="Paras elokuva ikinä!",
        source_url="https://ksml.fi/test1"
    )
    
    # Matti kirjoittaa myös elokuvasta 2, molempiin medioihin
    review4_hs = DBReview(
        movie_id=movie2.id,
        critic_id=critic_multi.id,
        publication_id=hs.id,
        rating_stars=2,
        review_text="Ei ihan parasta. (HS)",
        source_url="https://hs.fi/test3"
    )
    
    review4_ts = DBReview(
        movie_id=movie2.id,
        critic_id=critic_multi.id,
        publication_id=ts.id,
        rating_stars=3,
        review_text="Ihan siedettävä. (TS)",
        source_url="https://ts.fi/test2"
    )
    
    session.add_all([review1_hs, review1_ts, review2_hs, review3_ksml, review4_hs, review4_ts])
    session.commit()
    
    print("✅ Testidata lisätty!")
    print("\n📊 Yhteenveto:")
    print(f"  - Elokuvat: 2")
    print(f"  - Kriitikot: 3 (joista Matti Meikäläinen kirjoittaa SEKÄ HS:ään ETTÄ TS:ään)")
    print(f"  - Arvostelut: 6")
    print("\n🎬 Odotettu tulos:")
    print("  - Matti Meikäläisen sarake näyttää:")
    print("    * Testielokuva 1: ★★★★ [HS]  ★★★★★ [TS]")
    print("    * Testielokuva 2: ★★ [HS]  ★★★ [TS]")
    
except Exception as e:
    print(f"❌ Virhe: {e}")
    session.rollback()
    raise

finally:
    session.close()
