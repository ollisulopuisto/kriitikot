"""
Flask-pohjainen web-sovellus elokuva-arvostelujen näyttämiseen.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
from models import get_engine, get_session, session_scope, Movie, Critic, Publication, Review as DBReview
from services.data_service import DataService
from services.merge_service import merge_movies as merge_movie_records
from sqlalchemy.orm import joinedload
from functools import wraps
import xml.etree.ElementTree as ET
from email.utils import formatdate


app = Flask(__name__, template_folder='../templates', static_folder='../static')

APP_VERSION = "2026.03.13.9"

# Tietokantayhteys
engine = get_engine()
data_service = DataService(engine)


def admin_redirect(message: str, message_type: str = 'success'):
    """Ohjaa admin-näkymään viestin kanssa."""
    return redirect(url_for('admin', message=message, message_type=message_type))


def admin_action(fn):
    """Admin-reitin kääre: avaa session, rollback ja virheviesti poikkeuksessa.

    Kääritty funktio saa sessionin ensimmäisenä argumenttinaan.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        session = get_session(engine)
        try:
            return fn(session, *args, **kwargs)
        except Exception as e:
            session.rollback()
            return admin_redirect(f'Virhe: {str(e)}', 'error')
        finally:
            session.close()
    return wrapper


def delete_with_reviews(session, entity, label: str, name: str):
    """Poista entiteetti ja sen arvostelut. Palauttaa admin-redirectin."""
    review_count = len(entity.reviews)

    for review in list(entity.reviews):
        session.delete(review)

    session.delete(entity)
    session.commit()

    msg = f'{label} "{name}" poistettu'
    if review_count > 0:
        msg += f' ({review_count} arvostelua poistettu)'

    return admin_redirect(msg)


def get_all_reviews_grouped():
    """Hakee kaikki arvostelut ryhmiteltynä elokuvittain.

    DEPRECATED: Käytä data_service.get_grouped_reviews()
    Pidetty toistaiseksi yhteensopivuuden vuoksi.
    """
    with session_scope(engine) as session:
        return data_service.get_grouped_reviews(session)


@app.route('/reviews.json')
def reviews_json():
    """Kaikki arvostelut JSON-tiedostona (ladataan sivulle laiskasti)."""
    response = make_response(data_service.get_reviews_json())
    response.mimetype = 'application/json'
    return response


@app.route('/')
def index():
    """Etusivu - näyttää kaikki arvostelut."""
    # Hae kritikoiden järjestys query parametrista (CSV)
    order_str = request.args.get('order')
    order_ids = None
    if order_str:
        try:
            order_ids = [int(id_str) for id_str in order_str.split(',')]
        except (ValueError):
            pass

    data = data_service.get_index_data(critic_order_ids=order_ids)
    
    return render_template(
        'index.html',
        version=APP_VERSION,
        **data
    )



@app.route('/api/reviews', methods=['GET'])
def api_reviews():
    try:
        with session_scope(engine) as session:
            offset = request.args.get('offset', type=int, default=0)
            limit = request.args.get('limit', type=int, default=50)

            # Build the base query
            reviews_query = session.query(DBReview).options(
                joinedload(DBReview.movie),
                joinedload(DBReview.critic),
                joinedload(DBReview.publication)
            ).filter_by(is_published=1).order_by(DBReview.scraped_at.desc())

            # Get total count before applying limit and offset
            total_reviews = reviews_query.count()

            # Apply limit and offset
            reviews = reviews_query.offset(offset).limit(limit).all()

            return jsonify({
                'reviews': [review.to_dict() for review in reviews],
                'total_reviews': total_reviews,
                'offset': offset,
                'limit': limit
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/movies', methods=['GET'])
def api_movies():
    """JSON API - palauttaa elokuvia ja niiden arvosteluja ryhmiteltynä, tukee sivutusta."""
    offset = request.args.get('offset', type=int, default=0)
    limit = request.args.get('limit', type=int, default=50)
    
    data = data_service.get_paged_movies(offset, limit)
    
    if not data['paged_titles']:
        return jsonify({'movies_html': '', 'cards_html': '', 'count': 0, 'total': data['total']})
    
    # Renderöi HTML-pätkät
    movies_html = ""
    cards_html = ""
    
    for movie_title, critics_reviews in data['grouped_reviews'].items():
        # Helpers for template
        context = {
            'movie_title': movie_title,
            'critics_reviews': critics_reviews,
            'all_critics': data['all_critics'],
            **data['meta']
        }
        movies_html += render_template('_movie_row.html', **context)
        cards_html += render_template('_movie_card.html', **context)
            
    return jsonify({
        'movies_html': movies_html,
        'cards_html': cards_html,
        'count': len(data['paged_titles']),
        'total': data['total'],
        'offset': offset,
        'limit': limit
    })



@app.route('/health')
def health():
    """Terveystarkastus."""
    with session_scope(engine) as session:
        count = session.query(DBReview).count()
        return jsonify({
            'status': 'ok',
            'reviews_count': count
        })


@app.route('/rss')
@app.route('/rss.xml')
@app.route('/feed')
@app.route('/feed.xml')
def rss_feed():
    """Generoi RSS-syöte uusimmista arvosteluista."""
    try:
        with session_scope(engine) as session:
            # Hae 50 viimeisintä julkaistua arviota
            reviews = session.query(DBReview).filter_by(is_published=1).order_by(
                DBReview.scraped_at.desc()
            ).options(
                joinedload(DBReview.movie),
                joinedload(DBReview.critic),
                joinedload(DBReview.publication)
            ).limit(50).all()
        
            # Luo RSS XML
            rss = ET.Element('rss', version='2.0')
            channel = ET.SubElement(rss, 'channel')
        
            ET.SubElement(channel, 'title').text = 'Kriitikkojen valinta - Uusimmat arviot'
            ET.SubElement(channel, 'link').text = 'https://ollisulopuisto.github.io/kriitikot/'
            ET.SubElement(channel, 'description').text = 'Suomalaisten kriitikoiden elokuva-arvostelut.'
            ET.SubElement(channel, 'language').text = 'fi'
        
            if reviews:
                latest_date = reviews[0].published_date or reviews[0].scraped_at
                if latest_date:
                    ET.SubElement(channel, 'lastBuildDate').text = formatdate(latest_date.timestamp())
        
            for review in reviews:
                item = ET.SubElement(channel, 'item')
            
                movie_title = review.movie.title
                critic = review.critic.name
                pub = review.publication.name
                stars = f"{review.rating_stars}/5" if review.rating_stars else "Ei tähtiä"
            
                title = f"{movie_title} - {stars} - {critic} ({pub})"
                ET.SubElement(item, 'title').text = title
            
                # Käytä alkuperäistä URL-osoitetta linkkinä
                if review.source_url:
                    ET.SubElement(item, 'link').text = review.source_url
                    ET.SubElement(item, 'guid').text = review.source_url
            
                desc = f"Elokuva: {movie_title}\nKriitikko: {critic}\nJulkaisu: {pub}\nArvosana: {stars}"
                if review.review_text:
                    # Ota vain ensimmäinen kappale
                    text = review.review_text.strip()
                    if '\n\n' in text:
                        text = text.split('\n\n')[0]
                    elif '\n' in text:
                        # Jos ei tuplarivinvaihtoa, kokeile yksittäistä jos se vaikuttaa kappalejaolta
                        # (mutta varo listauksia tms).
                        # Yksinkertaisuuden vuoksi otetaan ensimmäinen "kappale" 
                        # joka on joko double newline tai jos ei ole, niin koko teksti.
                        # Mutta jos teksti on hyvin pitkä ja siinä on single newlineja, saatetaan haluta katkaista.
                        pass
                
                    # Varmistus: jos silti liian pitkä (yli 500 merkkiä), katkaise
                    if len(text) > 500:
                        text = text[:500] + "..."
                
                    desc += f"\n\n{text}"
            
                ET.SubElement(item, 'description').text = desc
            
                pub_date = review.published_date or review.scraped_at
                if pub_date:
                    ET.SubElement(item, 'pubDate').text = formatdate(pub_date.timestamp())
                
            response = make_response(ET.tostring(rss, encoding='utf-8', method='xml'))
            response.headers['Content-Type'] = 'application/xml; charset=utf-8'
            return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin')
def admin():
    """Admin-sivu elokuvanimien hallintaan."""
    with session_scope(engine) as session:
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


@app.route('/admin/movie/<int:movie_id>/rename', methods=['POST'])
@admin_action
def rename_movie(session, movie_id):
    """Nimeä elokuva uudelleen."""
    movie = session.get(Movie, movie_id)
    if not movie:
        return admin_redirect('Elokuvaa ei löytynyt', 'error')

    new_title = request.form.get('new_title', '').strip()
    if not new_title:
        return admin_redirect('Nimi ei voi olla tyhjä', 'error')

    old_title = movie.title
    movie.title = new_title
    session.commit()

    return admin_redirect(f'Elokuva "{old_title}" → "{new_title}" päivitetty!')


@app.route('/admin/movie/<int:movie_id>/delete', methods=['POST'])
@admin_action
def delete_movie(session, movie_id):
    """Poista elokuva JA kaikki sen arvostelut (cascade delete)."""
    movie = session.get(Movie, movie_id)
    if not movie:
        return admin_redirect('Elokuvaa ei löytynyt', 'error')

    return delete_with_reviews(session, movie, 'Elokuva', movie.title)


@app.route('/admin/movie/merge', methods=['POST'])
@admin_action
def merge_movies(session):
    """Yhdistä kaksi elokuvaa (siirrä arvostelut toiseen ja poista toinen)."""
    source_id = int(request.form.get('source_id'))
    target_id = int(request.form.get('target_id'))

    if source_id == target_id:
        return admin_redirect('Lähde ja kohde eivät voi olla sama elokuva', 'error')

    result = merge_movie_records(session, canonical_id=target_id, duplicate_id=source_id)
    if result is None:
        return admin_redirect('Elokuvia ei löytynyt', 'error')

    session.commit()

    msg = (f'✅ Yhdistetty "{result.duplicate_title}" → "{result.canonical_title}" '
           f'({result.moved} arvostelua siirretty)')
    if result.dropped:
        msg += f', {result.dropped} päällekkäistä arvostelua poistettu'
    if result.carried_metadata:
        msg += f', metatiedot siirretty: {", ".join(result.carried_metadata)}'

    return admin_redirect(msg)


@app.route('/admin/critic/<int:critic_id>/delete', methods=['POST'])
@admin_action
def delete_critic(session, critic_id):
    """Poista kriitikko JA kaikki hänen arvostelunsa (cascade delete)."""
    critic = session.get(Critic, critic_id)
    if not critic:
        return admin_redirect('Kriitikkoa ei löytynyt', 'error')

    return delete_with_reviews(session, critic, 'Kriitikko', critic.name)


@app.route('/admin/review/<int:review_id>/publish', methods=['POST'])
@admin_action
def publish_review(session, review_id):
    """Julkaise pending-arvio."""
    review = session.get(DBReview, review_id)
    if not review:
        return admin_redirect('Arvostelua ei löytynyt', 'error')

    review.is_published = 1
    movie_title = review.movie.title if review.movie else 'Unknown'
    session.commit()

    return admin_redirect(f'✅ Arvio julkaistu: {movie_title}')


@app.route('/admin/review/<int:review_id>/unpublish', methods=['POST'])
@admin_action
def unpublish_review(session, review_id):
    """Poista arvio julkaisusta (piilota frontendistä)."""
    review = session.get(DBReview, review_id)
    if not review:
        return admin_redirect('Arvostelua ei löytynyt', 'error')

    review.is_published = 0
    movie_title = review.movie.title if review.movie else 'Unknown'
    session.commit()

    return admin_redirect(f'⏸️ Arvio piilotettu frontendistä: {movie_title}')


@app.route('/admin/review/<int:review_id>/delete', methods=['POST'])
@admin_action
def delete_review(session, review_id):
    """Poista arvio (esim. pending-tilasta)."""
    review = session.get(DBReview, review_id)
    if not review:
        return admin_redirect('Arvostelua ei löytynyt', 'error')

    movie_title = review.movie.title if review.movie else 'Unknown'
    session.delete(review)
    session.commit()

    return admin_redirect(f'Arvio poistettu: {movie_title}')


@app.route('/admin/movie/<int:movie_id>/fetch-metadata', methods=['POST'])
def fetch_movie_metadata(movie_id):
    """Hae elokuvan metatiedot automaattisesti."""
    from metadata_fetcher import MetadataFetcher
    
    try:
        data = request.get_json()
        movie_title = data.get('title', '')
        tmdb_id = data.get('tmdb_id', '').strip()
        
        if not movie_title:
            return jsonify({'error': 'Elokuvan nimi puuttuu'}), 400
        
        fetcher = MetadataFetcher()
        result = {}
        
        # Jos TMDB ID on annettu, käytä sitä suoraan
        if tmdb_id:
            # Poimi numeerinen ID URL:sta tai pelkästä ID:stä
            import re
            numeric_id = None
            
            # Jos URL, poimi ID siitä
            if 'themoviedb.org' in tmdb_id:
                match = re.search(r'/movie/(\d+)', tmdb_id)
                if match:
                    numeric_id = match.group(1)
            # Jos pelkkä numero
            elif tmdb_id.isdigit():
                numeric_id = tmdb_id
            
            if numeric_id:
                # Hae kaikki tiedot TMDB ID:llä (juliste + IMDB ID)
                details = fetcher.get_movie_details_tmdb(int(numeric_id))
                if details:
                    result['poster_url'] = details.get('poster_url')
                    result['tmdb_id'] = tmdb_id  # Palauta alkuperäinen arvo
                    result['imdb_id'] = details.get('imdb_id')
        else:
            # Jos TMDB ID:tä ei annettu, hae kaikki metatiedot normaalisti
            metadata = fetcher.fetch_all_metadata(movie_title)
            
            if metadata.get('tmdb_data'):
                tmdb = metadata['tmdb_data']
                result.update({
                    'tmdb_id': tmdb.get('tmdb_id'),
                    'poster_url': tmdb.get('poster_url'),
                    'imdb_id': tmdb.get('imdb_id')
                })
            
            if metadata.get('letterboxd_url'):
                result['letterboxd_url'] = metadata['letterboxd_url']
            
            if metadata.get('nytleffaan_url'):
                result['nytleffaan_url'] = metadata['nytleffaan_url']
        
        # Hae linkit aina (jos ei vielä haettu)
        if 'letterboxd_url' not in result:
            letterboxd_url = fetcher.generate_letterboxd_url(movie_title)
            if letterboxd_url:
                result['letterboxd_url'] = letterboxd_url
        
        if 'nytleffaan_url' not in result:
            nytleffaan_url = fetcher.generate_nytleffaan_url(movie_title)
            if nytleffaan_url:
                result['nytleffaan_url'] = nytleffaan_url
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/movie/<int:movie_id>/metadata', methods=['POST'])
@admin_action
def update_movie_metadata(session, movie_id):
    """Päivitä elokuvan metatiedot (TMDB, IMDB, jne)."""
    movie = session.get(Movie, movie_id)
    if not movie:
        return admin_redirect('Elokuvaa ei löytynyt', 'error')

    if request.form.get('tmdb_id'):
        movie.tmdb_id = int(request.form.get('tmdb_id'))

    for field in ('imdb_id', 'poster_url', 'letterboxd_url', 'nytleffaan_url'):
        value = request.form.get(field)
        if value:
            setattr(movie, field, value.strip())

    title = movie.title
    session.commit()

    return admin_redirect(f'✅ Metatiedot päivitetty: {title}')


@app.route('/debug/movies')
def debug_movies():
    """Debug - listaa kaikkien elokuvien ID:t ja nimet."""
    with session_scope(engine) as session:
        movies = session.query(Movie).all()
        return '<br>'.join([f"{m.id}: {m.title}" for m in movies])


@app.route('/admin/fetch-all-metadata', methods=['POST'])
def fetch_all_metadata():
    """Hae metatiedot kaikille elokuville joilla niitä puuttuu."""
    from metadata_fetcher import MetadataFetcher, backfill_movie_metadata
    import time

    fetcher = MetadataFetcher()
    updated = 0

    try:
        with session_scope(engine) as session:
            # Hae elokuvat joilla puuttuu TMDB ID tai poster
            movies = session.query(Movie).filter(
                (Movie.tmdb_id.is_(None)) |
                (Movie.poster_url.is_(None)) |
                (Movie.imdb_id.is_(None))
            ).all()

            for movie in movies:
                try:
                    if backfill_movie_metadata(movie, fetcher):
                        updated += 1

                    # Rate limiting - odota 1 sekunti jokaisen hakemisen jälkeen
                    time.sleep(1)

                except Exception as e:
                    print(f"Virhe elokuvan {movie.title} metatietojen haussa: {e}")
                    continue

            session.commit()

        return jsonify({
            'message': f'✅ Metatiedot haettu onnistuneesti {updated} elokuvalle',
            'updated': updated
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Elokuvakritiikkien Kerääjä Web App')
    parser.add_argument('--port', type=int, default=5432, help='Port to run the server on (default: 5432)')
    
    args = parser.parse_args()
    
    print("Starting Flask app with SQLite database")
    print(f"Open http://localhost:{args.port} to view reviews")
    
    app.run(debug=True, host='0.0.0.0', port=args.port)
