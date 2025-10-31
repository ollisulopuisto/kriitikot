# Datamallin muutos: Kriitikko useissa medioissa

## Ongelma

Nykyinen tietokantamalli ei tue tilannetta, jossa sama kriitikko kirjoittaa useampaan mediaan:

1. **Critic-taulussa** `media` on yksittäinen kenttä
2. **App.py** ryhmittelee arvostelut `kriitikon nimen` mukaan → ylikirjoittaa
3. **Template** olettaa: 1 kriitikko = 1 sarake = 1 arvostelu per elokuva

## Ratkaisu A: Kevyt muutos (suositus)

**Poista `media` Critic-taulusta** ja luota **composite key** Review-taululla:

```python
class Critic(Base):
    __tablename__ = 'critics'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)  # Vain nimi
    # POISTETTU: media
    
class Review(Base):
    __tablename__ = 'reviews'
    
    # ... muut kentät ...
    critic_id = Column(Integer, ForeignKey('critics.id'))
    publication_id = Column(Integer, ForeignKey('publications.id'))
    
    # Unique constraint: sama kriitikko voi arvostella saman elokuvan vain kerran per julkaisu
    __table_args__ = (
        UniqueConstraint('movie_id', 'critic_id', 'publication_id', name='_movie_critic_pub_uc'),
    )
```

**Edut:**
- Kriitikko voi kirjoittaa moneen mediaan
- Review yhdistää kriitikon, elokuvan JA julkaisun
- Ei tarvitse many-to-many taulua

**App.py muutos:**
```python
# NYT: grouped[movie_title][critic_name] = review
# UUSI: grouped[movie_title][critic_name] = []  # LISTA arvosteluja

for review in reviews:
    movie_title = review.movie.title
    critic_name = review.critic.name
    
    if movie_title not in grouped:
        grouped[movie_title] = {}
    
    if critic_name not in grouped[movie_title]:
        grouped[movie_title][critic_name] = []
    
    grouped[movie_title][critic_name].append(review)  # LISTA
```

**Template muutos:**

Taulukon solu voi sisältää USEITA linkkejä:

```html
<td class="rating-cell">
    {% if critic.name in critics_reviews %}
        {% set reviews_list = critics_reviews[critic.name] %}
        {% for review in reviews_list %}
            {% if review.source_url %}
            <a href="{{ review.source_url }}" target="_blank" title="{{ review.publication.name }}">
                {% if review.rating_stars %}
                <span class="rating-stars">{{ '★' * review.rating_stars }}</span>
                {% endif %}
                <span class="pub-badge">{{ review.publication.short_name }}</span>
            </a>
            {% endif %}
        {% endfor %}
    {% endif %}
</td>
```

## Ratkaisu B: Many-to-many (kompleksimpi)

Luo **CriticPublication** junction-taulu:

```python
class CriticPublication(Base):
    __tablename__ = 'critic_publications'
    
    id = Column(Integer, primary_key=True)
    critic_id = Column(Integer, ForeignKey('critics.id'))
    publication_id = Column(Integer, ForeignKey('publications.id'))
    
    __table_args__ = (
        UniqueConstraint('critic_id', 'publication_id'),
    )
```

**Haitat:**
- Monimutkaistaa dataa
- Vaatii ylimääräisen taulun
- Review viittaa edelleen publication_id:hen, joten tämä ei anna lisäarvoa

## Migraatio

### 1. Luo uusi tietokanta rinnalle
```bash
python3 -c "from models import init_db; init_db('reviews_new.db')"
```

### 2. Migroi data vanhasta uuteen
```python
# Lue vanha data, kirjoita uuteen formaattiin
# Critic.media → Review.publication_id (jo olemassa!)
```

### 3. Korvaa vanha tietokanta
```bash
mv reviews.db reviews_old.db
mv reviews_new.db reviews.db
```

## Yhteenveto

**Suositus: Ratkaisu A**
- Poista `Critic.media`
- Muuta app.py ryhmittely listaksi
- Muuta template näyttämään useita arvosteluja per solu
- Lisää `pub-badge` CSS-elementti julkaisun tunnukselle (HS, IL, jne.)

**Onko mahdollista?** ✅ KYLLÄ, muutokset ovat suoraviivaisia.

**Rikkooko olemassa olevan datan?** ⚠️ Tarvitaan migraatioskripti, mutta nykydata on pieni (21 arvostelua) joten voidaan jopa generoida uudelleen.
