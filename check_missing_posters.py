
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from models import get_session, Movie

def main():
    session = get_session()
    movies_without_posters = session.query(Movie).filter((Movie.poster_url == None) | (Movie.poster_url == '')).all()
    print(f"Total movies: {session.query(Movie).count()}")
    print(f"Movies without posters: {len(movies_without_posters)}")
    for m in movies_without_posters[:20]:
        print(f" - {m.title} (ID: {m.id})")
    if len(movies_without_posters) > 20:
        print("...")

if __name__ == '__main__':
    main()
