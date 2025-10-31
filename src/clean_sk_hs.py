#!/usr/bin/env python3
"""
Poista SK:n ja HS:n arvostelut tietokannasta.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models import get_session, Publication, Review as DBReview

session = get_session()

try:
    # Hae SK ja HS julkaisut
    sk = session.query(Publication).filter_by(short_name='sk').first()
    hs = session.query(Publication).filter_by(short_name='hs').first()
    
    if not sk or not hs:
        print("❌ SK tai HS julkaisua ei löytynyt!")
        sys.exit(1)
    
    # Poista SK:n arvostelut
    sk_reviews = session.query(DBReview).filter_by(publication_id=sk.id).all()
    sk_count = len(sk_reviews)
    for review in sk_reviews:
        session.delete(review)
    print(f"🗑️  Poistettu {sk_count} SK-arvostelua")
    
    # Poista HS:n arvostelut
    hs_reviews = session.query(DBReview).filter_by(publication_id=hs.id).all()
    hs_count = len(hs_reviews)
    for review in hs_reviews:
        session.delete(review)
    print(f"🗑️  Poistettu {hs_count} HS-arvostelua")
    
    session.commit()
    
    print(f"\n✅ Yhteensä poistettu {sk_count + hs_count} arvostelua")
    print(f"\n📊 Tietokannan tila:")
    print(f"  - Arvosteluja jäljellä: {session.query(DBReview).count()}")
    
except Exception as e:
    print(f"❌ Virhe: {e}")
    session.rollback()
    raise

finally:
    session.close()
