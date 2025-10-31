"""
Flask-pohjainen web-sovellus elokuva-arvostelujen näyttämiseen.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from models import get_engine, get_session, Movie, Critic, Publication, Review as DBReview
from sqlalchemy.orm import joinedload
from typing import List, Dict
import os


app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Tietokantayhteys
engine = get_engine()


def get_all_reviews_grouped():
    """Hakee kaikki arvostelut ryhmiteltynä elokuvittain.
    
    Palauttaa:
        - grouped: dict[movie_title][critic_name] = [review1, review2, ...]
        - critics: List[Critic] - kaikki kriitikot
        - total_reviews: int - arvostelujen määrä
    """
    session = get_session(engine)
    
    try:
        # Hae kaikki JULKAISTUT arvostelut EAGER LOADingilla (lataa relaatiot heti)
        reviews = session.query(DBReview).filter_by(is_published=1).options(
            joinedload(DBReview.movie),
            joinedload(DBReview.critic),
            joinedload(DBReview.publication)
        ).all()
        
        # Hae kaikki kriitikot
        critics = session.query(Critic).all()
        
        # Ryhmittele elokuvittain (kriitikon NIMI → LISTA arvosteluja)
        grouped = {}
        
        for review in reviews:
            movie_title = review.movie.title
            critic_name = review.critic.name
            
            if movie_title not in grouped:
                grouped[movie_title] = {}
            
            if critic_name not in grouped[movie_title]:
                grouped[movie_title][critic_name] = []
            
            # Lisää arvostelu listaan (sama kriitikko voi olla useassa mediassa)
            grouped[movie_title][critic_name].append(review)
        
        return grouped, sorted(critics, key=lambda c: c.name), len(reviews)
    
    finally:
        session.close()


@app.route('/')
def index():
    """Etusivu - näyttää kaikki arvostelut."""
    grouped_reviews, all_critics, total_reviews = get_all_reviews_grouped()
    
    # Hae kritikoiden järjestys query parametrista (CSV)
    order = request.args.get('order')
    if order:
        try:
            critic_ids = [int(id) for id in order.split(',')]
            # Järjestä kriitikot annetun järjestyksen mukaan
            critic_dict = {c.id: c for c in all_critics}
            ordered_critics = [critic_dict[id] for id in critic_ids if id in critic_dict]
            # Lisää loput kriitikot jotka eivät ole järjestyksessä
            remaining = [c for c in all_critics if c.id not in critic_ids]
            all_critics = ordered_critics + remaining
        except (ValueError, KeyError):
            pass  # Jos virhe, käytä oletusta
    
    # Laske kritikoiden mediat (kriitikko voi kirjoittaa useaan mediaan)
    session = get_session(engine)
    try:
        critic_media_map = {}  # critic_id -> list of publication short_names
        for critic in all_critics:
            # Hae kaikki kriitikon arvostelut
            reviews = session.query(DBReview).filter(
                DBReview.critic_id == critic.id
            ).options(joinedload(DBReview.publication)).all()
            
            # Kerää uniikit julkaisut
            publications = list(set([r.publication.short_name.upper() for r in reviews if r.publication]))
            publications.sort()  # Aakkosjärjestys
            critic_media_map[critic.id] = publications
        
        # Laske arvosanajakauma
        rating_distribution = {}
        for i in range(1, 6):
            count = session.query(DBReview).filter(DBReview.rating_stars == i).count()
            rating_distribution[i] = count
        
        # Julkaisujen tilastot
        publications = session.query(Publication).all()
        pub_stats = {}
        for pub in publications:
            review_count = session.query(DBReview).filter(DBReview.publication_id == pub.id).count()
            if review_count > 0:
                pub_stats[pub.short_name.upper()] = review_count
    finally:
        session.close()
    
    return render_template(
        'index.html',
        grouped_reviews=grouped_reviews,
        all_critics=all_critics,
        total_reviews=total_reviews,
        rating_distribution=rating_distribution,
        pub_stats=pub_stats,
        critic_media_map=critic_media_map
    )


@app.route('/api/reviews')
def api_reviews():
    """JSON API - palauttaa kaikki JULKAISTUT arvostelut."""
    session = get_session(engine)
    
    try:
        reviews = session.query(DBReview).filter_by(is_published=1).all()
        return jsonify([review.to_dict() for review in reviews])
    finally:
        session.close()


@app.route('/api/reviews/<int:review_id>')
def api_review(review_id):
    """JSON API - palauttaa yhden arvostelun."""
    session = get_session(engine)
    
    try:
        review = session.query(DBReview).get(review_id)
        if review:
            return jsonify(review.to_dict())
        return jsonify({'error': 'Review not found'}), 404
    finally:
        session.close()


@app.route('/health')
def health():
    """Terveystarkastus."""
    session = get_session(engine)
    
    try:
        count = session.query(DBReview).count()
        return jsonify({
            'status': 'ok',
            'reviews_count': count
        })
    finally:
        session.close()


@app.route('/admin')
def admin():
    """Admin-sivu elokuvanimien hallintaan."""
    session = get_session(engine)
    
    try:
        movies = session.query(Movie).options(joinedload(Movie.reviews)).all()
        critics = session.query(Critic).options(
            joinedload(Critic.reviews).joinedload(DBReview.publication)
        ).all()
        
        # Hae pending-arviot (ei vielä julkaistut)
        pending_reviews = session.query(DBReview).filter_by(is_published=0).options(
            joinedload(DBReview.movie),
            joinedload(DBReview.critic),
            joinedload(DBReview.publication)
        ).order_by(DBReview.scraped_at.desc()).all()
        
        # Aakkosta elokuvat ja kriitikot nimen mukaan
        movies = sorted(movies, key=lambda m: m.title.lower())
        critics = sorted(critics, key=lambda c: c.name.lower())
        
        # Laske kritikoiden mediat
        critic_media_map = {}
        for critic in critics:
            publications = list(set([r.publication.short_name.upper() for r in critic.reviews if r.publication]))
            publications.sort()
            critic_media_map[critic.id] = ', '.join(publications) if publications else '–'
        
        stats = {
            'movies': session.query(Movie).count(),
            'reviews': session.query(DBReview).count(),
            'critics': session.query(Critic).count(),
            'publications': session.query(Publication).count(),
            'pending': len(pending_reviews)
        }
        
        # Hae mahdollinen viesti session storagesta (flash-viestit)
        message = request.args.get('message')
        message_type = request.args.get('message_type', 'success')
        
        return render_template(
            'admin.html',
            movies=movies,
            critics=critics,
            critic_media_map=critic_media_map,
            pending_reviews=pending_reviews,
            stats=stats,
            message=message,
            message_type=message_type
        )
    finally:
        session.close()


@app.route('/admin/movie/<int:movie_id>/rename', methods=['POST'])
def rename_movie(movie_id):
    """Nimeä elokuva uudelleen."""
    session = get_session(engine)
    
    try:
        movie = session.query(Movie).get(movie_id)
        if not movie:
            return redirect(url_for('admin', message='Elokuvaa ei löytynyt', message_type='error'))
        
        new_title = request.form.get('new_title', '').strip()
        if not new_title:
            return redirect(url_for('admin', message='Nimi ei voi olla tyhjä', message_type='error'))
        
        old_title = movie.title
        movie.title = new_title
        session.commit()
        
        return redirect(url_for('admin', message=f'Elokuva "{old_title}" → "{new_title}" päivitetty!', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/movie/<int:movie_id>/delete', methods=['POST'])
def delete_movie(movie_id):
    """Poista elokuva JA kaikki sen arvostelut (cascade delete)."""
    session = get_session(engine)
    
    try:
        movie = session.query(Movie).get(movie_id)
        if not movie:
            return redirect(url_for('admin', message='Elokuvaa ei löytynyt', message_type='error'))
        
        title = movie.title
        review_count = len(movie.reviews)
        
        # Poista kaikki arvostelut ensin
        for review in movie.reviews:
            session.delete(review)
        
        # Poista elokuva
        session.delete(movie)
        session.commit()
        
        msg = f'Elokuva "{title}" poistettu'
        if review_count > 0:
            msg += f' ({review_count} arvostelua poistettu)'
        
        return redirect(url_for('admin', message=msg, message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/movie/merge', methods=['POST'])
def merge_movies():
    """Yhdistä kaksi elokuvaa (siirrä arvostelut toiseen ja poista toinen)."""
    session = get_session(engine)
    
    try:
        source_id = int(request.form.get('source_id'))
        target_id = int(request.form.get('target_id'))
        
        if source_id == target_id:
            return redirect(url_for('admin', message='Lähde ja kohde eivät voi olla sama elokuva', message_type='error'))
        
        source = session.query(Movie).get(source_id)
        target = session.query(Movie).get(target_id)
        
        if not source or not target:
            return redirect(url_for('admin', message='Elokuvia ei löytynyt', message_type='error'))
        
        # Siirrä kaikki arvostelut lähteestä kohteeseen
        review_count = len(source.reviews)
        for review in source.reviews:
            review.movie = target
        
        # Poista lähde-elokuva
        source_title = source.title
        session.delete(source)
        session.commit()
        
        return redirect(url_for('admin', 
            message=f'✅ Yhdistetty "{source_title}" → "{target.title}" ({review_count} arvostelua siirretty)', 
            message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()




@app.route('/admin/critic/<int:critic_id>/delete', methods=['POST'])
def delete_critic(critic_id):
    """Poista kriitikko JA kaikki hänen arvostelunsa (cascade delete)."""
    session = get_session(engine)
    
    try:
        critic = session.query(Critic).get(critic_id)
        if not critic:
            return redirect(url_for('admin', message='Kriitikkoa ei löytynyt', message_type='error'))
        
        name = critic.name
        review_count = len(critic.reviews)
        
        # Poista kaikki arvostelut ensin
        for review in critic.reviews:
            session.delete(review)
        
        # Poista kriitikko
        session.delete(critic)
        session.commit()
        
        msg = f'Kriitikko "{name}" poistettu'
        if review_count > 0:
            msg += f' ({review_count} arvostelua poistettu)'
        
        return redirect(url_for('admin', message=msg, message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/review/<int:review_id>/publish', methods=['POST'])
def publish_review(review_id):
    """Julkaise pending-arvio."""
    session = get_session(engine)
    
    try:
        review = session.query(DBReview).get(review_id)
        if not review:
            return redirect(url_for('admin', message='Arvostelua ei löytynyt', message_type='error'))
        
        review.is_published = 1
        session.commit()
        
        movie_title = review.movie.title if review.movie else 'Unknown'
        return redirect(url_for('admin', message=f'✅ Arvio julkaistu: {movie_title}', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/review/<int:review_id>/unpublish', methods=['POST'])
def unpublish_review(review_id):
    """Poista arvio julkaisusta (piilota frontendistä)."""
    session = get_session(engine)
    
    try:
        review = session.query(DBReview).get(review_id)
        if not review:
            return redirect(url_for('admin', message='Arvostelua ei löytynyt', message_type='error'))
        
        review.is_published = 0
        session.commit()
        
        movie_title = review.movie.title if review.movie else 'Unknown'
        return redirect(url_for('admin', message=f'⏸️ Arvio piilotettu frontendistä: {movie_title}', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/review/<int:review_id>/delete', methods=['POST'])
def delete_review(review_id):
    """Poista arvio (esim. pending-tilasta)."""
    session = get_session(engine)
    
    try:
        review = session.query(DBReview).get(review_id)
        if not review:
            return redirect(url_for('admin', message='Arvostelua ei löytynyt', message_type='error'))
        
        movie_title = review.movie.title if review.movie else 'Unknown'
        session.delete(review)
        session.commit()
        
        return redirect(url_for('admin', message=f'Arvio poistettu: {movie_title}', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/movie/<int:movie_id>/metadata', methods=['POST'])
def update_movie_metadata(movie_id):
    """Päivitä elokuvan metatiedot (TMDB, IMDB, jne)."""
    session = get_session(engine)
    
    try:
        movie = session.query(Movie).get(movie_id)
        if not movie:
            return redirect(url_for('admin', message='Elokuvaa ei löytynyt', message_type='error'))
        
        # Päivitä kentät
        if request.form.get('tmdb_id'):
            movie.tmdb_id = int(request.form.get('tmdb_id'))
        
        if request.form.get('imdb_id'):
            movie.imdb_id = request.form.get('imdb_id').strip()
        
        if request.form.get('poster_url'):
            movie.poster_url = request.form.get('poster_url').strip()
        
        if request.form.get('letterboxd_url'):
            movie.letterboxd_url = request.form.get('letterboxd_url').strip()
        
        session.commit()
        
        return redirect(url_for('admin', message=f'✅ Metatiedot päivitetty: {movie.title}', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


if __name__ == '__main__':
    print(f"Starting Flask app with SQLite database")
    print("Open http://localhost:5000 to view reviews")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
