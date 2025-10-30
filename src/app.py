"""
Flask-pohjainen web-sovellus elokuva-arvostelujen näyttämiseen.
"""

from flask import Flask, render_template, jsonify
from scraper import HSScraper, Review
from typing import List
import os


app = Flask(__name__, template_folder='../templates')


# Väliaikainen "tietokanta" - myöhemmin korvataan MySQL:llä
DEMO_REVIEWS: List[Review] = []


def load_demo_data():
    """Lataa demo-arvostelut testidatasta."""
    test_file = os.path.join(
        os.path.dirname(__file__),
        '../tests/test_data/hs_review_1.html'
    )
    
    if os.path.exists(test_file):
        scraper = HSScraper()
        review = scraper.parse_file(test_file)
        if review:
            DEMO_REVIEWS.append(review)


@app.route('/')
def index():
    """Pääsivu - näyttää kaikki arvostelut."""
    return render_template('index.html', reviews=DEMO_REVIEWS)


@app.route('/api/reviews')
def api_reviews():
    """JSON API - palauttaa kaikki arvostelut."""
    return jsonify([review.to_dict() for review in DEMO_REVIEWS])


@app.route('/api/reviews/<int:index>')
def api_review(index):
    """JSON API - palauttaa yhden arvostelun."""
    if 0 <= index < len(DEMO_REVIEWS):
        return jsonify(DEMO_REVIEWS[index].to_dict())
    return jsonify({'error': 'Review not found'}), 404


@app.route('/health')
def health():
    """Terveystarkastus."""
    return jsonify({
        'status': 'ok',
        'reviews_count': len(DEMO_REVIEWS)
    })


if __name__ == '__main__':
    # Lataa demo-data käynnistyksen yhteydessä
    load_demo_data()
    
    print(f"Loaded {len(DEMO_REVIEWS)} demo reviews")
    print("Starting Flask app on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
