"""
Flask-pohjainen web-sovellus elokuva-arvostelujen näyttämiseen.
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from models import get_engine, get_session, Movie, Critic, Publication, Review as DBReview
from sqlalchemy.orm import joinedload
from datetime import datetime
try:
    # Python 3.9+: zoneinfo is preferred
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
import os
import xml.etree.ElementTree as ET
from email.utils import formatdate
from flask import make_response


app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Tietokantayhteys
engine = get_engine()


def get_all_reviews_grouped():
    """Hakee kaikki arvostelut ryhmiteltynä elokuvittain.
    
    Palauttaa:
        - grouped: OrderedDict[movie_title][critic_name] = [review1, review2, ...]
          Järjestetty uusimman arvion mukaan (uusin ensin)
        - critics: List[Critic] - kaikki kriitikot
        - total_reviews: int - arvostelujen määrä
    """
    from collections import OrderedDict
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
        movie_latest_review = {}  # Tallenna jokaisen elokuvan uusin arvio
        
        for review in reviews:
            movie_title = review.movie.title
            critic_name = review.critic.name
            
            if movie_title not in grouped:
                grouped[movie_title] = {}
            
            if critic_name not in grouped[movie_title]:
                grouped[movie_title][critic_name] = []
            
            # Lisää arvostelu listaan (sama kriitikko voi olla useassa mediassa)
            grouped[movie_title][critic_name].append(review)
            
            # Päivitä elokuvan uusin arvio
            # Käytä published_date jos saatavilla, muuten scraped_at
            review_date = review.published_date or review.scraped_at
            if movie_title not in movie_latest_review or review_date > movie_latest_review[movie_title]:
                movie_latest_review[movie_title] = review_date
        
        # Järjestä elokuvat uusimman arvion mukaan (uusin ensin)
        sorted_movies = sorted(
            grouped.keys(), 
            key=lambda title: movie_latest_review.get(title, datetime(1900, 1, 1)), 
            reverse=True
        )
        
        # Luo järjestetty dict
        grouped_ordered = OrderedDict()
        for movie_title in sorted_movies:
            grouped_ordered[movie_title] = grouped[movie_title]
        
        return grouped_ordered, sorted(critics, key=lambda c: c.name), len(reviews)
    
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
    
    # Laske arvioiden määrät elokuville ja kriitikoille
    movie_review_counts = {}
    for movie_title, critics_reviews in grouped_reviews.items():
        count = sum(len(reviews) for reviews in critics_reviews.values())
        movie_review_counts[movie_title] = count
    
    # Laske kritikoiden mediat (kriitikko voi kirjoittaa useaan mediaan)
    session = get_session(engine)
    try:
        critic_media_map = {}  # critic_id -> list of publication short_names
        critic_review_counts = {}  # critic_id -> review count
        for critic in all_critics:
            # Hae kaikki kriitikon arvostelut
            reviews = session.query(DBReview).filter(
                DBReview.critic_id == critic.id,
                DBReview.is_published == 1
            ).options(joinedload(DBReview.publication)).all()
            
            # Kerää uniikit julkaisut
            publications = list(set([r.publication.short_name.upper() for r in reviews if r.publication]))
            publications.sort()  # Aakkosjärjestys
            critic_media_map[critic.id] = publications
            critic_review_counts[critic.id] = len(reviews)
        
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
        
        # Aakkosta julkaisut
        pub_stats = dict(sorted(pub_stats.items(), key=lambda x: x[0]))
        
        # Hae nytleffaan.fi linkit ja posterit
        nytleffaan_urls = {}
        poster_urls = {}
        letterboxd_urls = {}
        movies = session.query(Movie).all()
        for movie in movies:
            if movie.nytleffaan_url:
                nytleffaan_urls[movie.title] = movie.nytleffaan_url
            if movie.poster_url:
                poster_urls[movie.title] = movie.poster_url
            if movie.letterboxd_url:
                letterboxd_urls[movie.title] = movie.letterboxd_url
        
        # Laske viimeisin päivitysaika (uusin scraped_at tai published_date)
        latest_update = session.query(DBReview).filter_by(is_published=1).order_by(
            DBReview.scraped_at.desc()
        ).first()
        last_updated = None
        if latest_update:
            # Käytä published_date jos saatavilla, muuten scraped_at
            last_updated = latest_update.published_date or latest_update.scraped_at
            # Normalize timezone: if datetime is naive, assume UTC, then convert
            # to desired display timezone. The display timezone can be set
            # via environment variable `DISPLAY_TIMEZONE` (default: Europe/Helsinki).
            display_tz = os.environ.get('DISPLAY_TIMEZONE', 'Europe/Helsinki')
            if ZoneInfo is not None and last_updated is not None:
                try:
                    if last_updated.tzinfo is None:
                        # Assume stored timestamps are in UTC if naive
                        last_updated = last_updated.replace(tzinfo=ZoneInfo('UTC'))
                    # Convert to target timezone
                    last_updated = last_updated.astimezone(ZoneInfo(display_tz))
                except Exception:
                    # If anything goes wrong with zoneinfo (unknown zone), leave as-is
                    pass
    finally:
        session.close()
    
    return render_template(
        'index.html',
        grouped_reviews=grouped_reviews,
        all_critics=all_critics,
        total_reviews=total_reviews,
        rating_distribution=rating_distribution,
        pub_stats=pub_stats,
        critic_media_map=critic_media_map,
        critic_review_counts=critic_review_counts,
        movie_review_counts=movie_review_counts,
        nytleffaan_urls=nytleffaan_urls,
        poster_urls=poster_urls,
        letterboxd_urls=letterboxd_urls,
        last_updated=last_updated
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


@app.route('/rss')
@app.route('/rss.xml')
@app.route('/feed')
@app.route('/feed.xml')
def rss_feed():
    """Generoi RSS-syöte uusimmista arvosteluista."""
    session = get_session(engine)
    
    try:
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
        # Iterate over a COPY of the list because modifying the relationship 
        # (review.movie = target) removes the item from source.reviews, 
        # causing the iterator to skip elements if iterating over the live list.
        for review in list(source.reviews):
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
        
        if request.form.get('nytleffaan_url'):
            movie.nytleffaan_url = request.form.get('nytleffaan_url').strip()
        
        session.commit()
        
        return redirect(url_for('admin', message=f'✅ Metatiedot päivitetty: {movie.title}', message_type='success'))
    
    except Exception as e:
        session.rollback()
        return redirect(url_for('admin', message=f'Virhe: {str(e)}', message_type='error'))
    
    finally:
        session.close()


@app.route('/debug/movies')
def debug_movies():
    """Debug - listaa kaikkien elokuvien ID:t ja nimet."""
    session = get_session(engine)
    
    try:
        movies = session.query(Movie).all()
        return '<br>'.join([f"{m.id}: {m.title}" for m in movies])
    finally:
        session.close()


@app.route('/admin/fetch-all-metadata', methods=['POST'])
def fetch_all_metadata():
    """Hae metatiedot kaikille elokuville joilla niitä puuttuu."""
    from metadata_fetcher import MetadataFetcher
    import time
    
    session = get_session(engine)
    fetcher = MetadataFetcher()
    updated = 0
    
    try:
        # Hae elokuvat joilla puuttuu TMDB ID tai poster
        movies = session.query(Movie).filter(
            (Movie.tmdb_id.is_(None)) | 
            (Movie.poster_url.is_(None)) |
            (Movie.imdb_id.is_(None))
        ).all()
        
        for movie in movies:
            try:
                metadata = fetcher.fetch_all_metadata(movie.title)
                
                if metadata.get('tmdb_data'):
                    tmdb = metadata['tmdb_data']
                    if not movie.tmdb_id:
                        movie.tmdb_id = tmdb['tmdb_id']
                    if not movie.poster_url:
                        movie.poster_url = tmdb['poster_url']
                
                if metadata.get('imdb_id') and not movie.imdb_id:
                    movie.imdb_id = metadata['imdb_id']
                
                if metadata.get('letterboxd_url') and not movie.letterboxd_url:
                    movie.letterboxd_url = metadata['letterboxd_url']
                
                if metadata.get('nytleffaan_url') and not movie.nytleffaan_url:
                    movie.nytleffaan_url = metadata['nytleffaan_url']
                
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
        session.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Elokuvakritiikkien Kerääjä Web App')
    parser.add_argument('--port', type=int, default=5432, help='Port to run the server on (default: 5432)')
    
    args = parser.parse_args()
    
    print("Starting Flask app with SQLite database")
    print(f"Open http://localhost:{args.port} to view reviews")
    
    app.run(debug=True, host='0.0.0.0', port=args.port)
