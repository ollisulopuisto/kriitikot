"""
Flask-pohjainen web-sovellus elokuva-arvostelujen näyttämiseen.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from models import get_engine, get_session, Movie, Critic, Publication, Review as DBReview
from sqlalchemy.orm import joinedload
from typing import List, Dict
import os


app = Flask(__name__, template_folder='../templates')

# Tietokantayhteys
engine = get_engine()


def get_all_reviews_grouped():
    """Hakee kaikki arvostelut ryhmiteltynä elokuvittain."""
    session = get_session(engine)
    
    try:
        # Hae kaikki arvostelut EAGER LOADingilla (lataa relaatiot heti)
        reviews = session.query(DBReview).options(
            joinedload(DBReview.movie),
            joinedload(DBReview.critic),
            joinedload(DBReview.publication)
        ).all()
        
        # Hae kaikki kriitikot
        critics = session.query(Critic).all()
        
        # Ryhmittele elokuvittain (käytä kriitikon NIMEÄ avaimena)
        grouped = {}
        
        for review in reviews:
            movie_title = review.movie.title
            critic_name = review.critic.name
            
            if movie_title not in grouped:
                grouped[movie_title] = {}
            
            grouped[movie_title][critic_name] = review
        
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
    
    return render_template(
        'index.html',
        grouped_reviews=grouped_reviews,
        all_critics=all_critics,
        total_reviews=total_reviews
    )


@app.route('/api/reviews')
def api_reviews():
    """JSON API - palauttaa kaikki arvostelut."""
    session = get_session(engine)
    
    try:
        reviews = session.query(DBReview).all()
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
        critics = session.query(Critic).options(joinedload(Critic.reviews)).all()
        
        stats = {
            'movies': session.query(Movie).count(),
            'reviews': session.query(DBReview).count(),
            'critics': session.query(Critic).count(),
            'publications': session.query(Publication).count()
        }
        
        # Hae mahdollinen viesti session storagesta (flash-viestit)
        message = request.args.get('message')
        message_type = request.args.get('message_type', 'success')
        
        return render_template(
            'admin.html',
            movies=movies,
            critics=critics,
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
    """Poista elokuva (vain jos ei arvosteluja)."""
    session = get_session(engine)
    
    try:
        movie = session.query(Movie).get(movie_id)
        if not movie:
            return redirect(url_for('admin', message='Elokuvaa ei löytynyt', message_type='error'))
        
        if len(movie.reviews) > 0:
            return redirect(url_for('admin', message='Elokuvaa ei voi poistaa - sillä on arvosteluja', message_type='error'))
        
        title = movie.title
        session.delete(movie)
        session.commit()
        
        return redirect(url_for('admin', message=f'Elokuva "{title}" poistettu', message_type='success'))
    
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


@app.route('/admin/critic/<int:critic_id>/update_media', methods=['POST'])
def update_critic_media(critic_id):
    """Päivitä kriitikon media."""
    session = get_session(engine)
    
    try:
        critic = session.query(Critic).get(critic_id)
        if not critic:
            return redirect(url_for('admin', message='Kriitikkoa ei löytynyt', message_type='error'))
        
        new_media = request.form.get('media', '').strip().upper()
        
        old_media = critic.media or '(ei mediaa)'
        critic.media = new_media if new_media else None
        session.commit()
        
        return redirect(url_for('admin', message=f'Kriitikko {critic.name}: media päivitetty "{old_media}" → "{new_media or "(ei mediaa)"}"', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/admin/critic/<int:critic_id>/delete', methods=['POST'])
def delete_critic(critic_id):
    """Poista kriitikko (vain jos ei arvosteluja)."""
    session = get_session(engine)
    
    try:
        critic = session.query(Critic).get(critic_id)
        if not critic:
            return redirect(url_for('admin', message='Kriitikkoa ei löytynyt', message_type='error'))
        
        if len(critic.reviews) > 0:
            return redirect(url_for('admin', message='Kriitikkoa ei voi poistaa - hänellä on arvosteluja', message_type='error'))
        
        name = critic.name
        session.delete(critic)
        session.commit()
        
        return redirect(url_for('admin', message=f'Kriitikko "{name}" poistettu', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


if __name__ == '__main__':
    print(f"Starting Flask app with SQLite database")
    print("Open http://localhost:5000 to view reviews")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
