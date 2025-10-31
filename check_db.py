#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

from models import get_session, Movie, Critic, Publication, Review

session = get_session()

print("📊 Tietokannan tila:")
print(f"  Movies: {session.query(Movie).count()}")
print(f"  Critics: {session.query(Critic).count()}")
print(f"  Publications: {session.query(Publication).count()}")
print(f"  Reviews: {session.query(Review).count()}")

print("\n🎬 Elokuvat:")
for movie in session.query(Movie).all():
    print(f"  - {movie.title}")

print("\n👤 Kriitikot:")
for critic in session.query(Critic).all():
    print(f"  - {critic.name}")

print("\n⭐ Arvostelut:")
for review in session.query(Review).limit(5).all():
    print(f"  - {review.movie.title} / {review.critic.name} / {review.publication.short_name.upper()} / {review.rating_stars}★")

session.close()
