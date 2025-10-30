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
        
        # Ryhmittele elokuvittain
        grouped = {}
        all_critics = set()
        
        for review in reviews:
            movie_title = review.movie.title
            critic_name = review.critic.name
            
            if movie_title not in grouped:
                grouped[movie_title] = {}
            
            grouped[movie_title][critic_name] = review
            all_critics.add(critic_name)
        
        return grouped, sorted(all_critics), len(reviews)
    
    finally:
        session.close()


@app.route('/')
def index():
    """Pääsivu - näyttää kaikki arvostelut ryhmiteltynä elokuvittain."""
    grouped, all_critics, total = get_all_reviews_grouped()
    
    return render_template(
        'index.html',
        grouped_reviews=grouped,
        all_critics=all_critics,
        total_reviews=total
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


if __name__ == '__main__':
    print(f"Starting Flask app with SQLite database")
    print("Open http://localhost:5000 to view reviews")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
