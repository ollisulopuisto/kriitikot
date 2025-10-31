#!/usr/bin/env python3

from models import db, Movie
from app import app

with app.app_context():
    movies = db.session.query(Movie).all()
    print(f"Total movies: {len(movies)}")
    for movie in movies[:10]:  # First 10
        print(f"ID: {movie.id}, Title: {movie.title}")