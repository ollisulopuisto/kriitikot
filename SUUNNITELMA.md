# Elokuvakritiikkien Kerääjä - Suunnitelma

Tämä dokumentti kuvaa web-sovelluksen suunnitelman, joka kerää, analysoi ja esittää elokuvakritiikkejä.

## 1. Vaatimukset

### Toiminnalliset vaatimukset
1.  **Datan keräys:** Järjestelmän tulee pystyä lataamaan määriteltyjen verkkosivujen HTML-sisältö.
2.  **Datan ekstraktointi:** Sivuilta tulee tunnistaa ja erottaa seuraavat tiedot:
    *   Kriitikon nimi
    *   Elokuvan nimi
    *   Arvostelun teksti
    *   Tähtiarvosana (jos saatavilla)
    *   Linkki alkuperäiseen arvosteluun
    *   Kriitikon profiilikuva (jos saatavilla)
3.  **Arvosanan generointi:** Jos tähtiarvosanaa ei löydy, arvostelun teksti tulee lähettää paikalliselle Ollama-kielimallille, joka generoi 1-5 tähden arvosanan.
4.  **Elokuvien normalisointi:** Eri tavoin kirjoitetut elokuvanimet (esim. "Dune 2", "Dune: Part two") tulee yhdistää yhdeksi normalisoiduksi nimeksi.
5.  **Datan tallennus:** Kerätty, käsitelty ja normalisoitu data tulee tallentaa MySQL-tietokantaan.
6.  **Esitysmuoto:** Järjestelmän tulee generoida HTML-tiedosto, joka näyttää datan taulukossa:
    *   Riveillä elokuvat.
    *   Sarakkeissa kriitikot (nimellä ja kuvalla).
    *   Soluissa kunkin kriitikon antama tähtiarvosana elokuvalle.
    *   Arvosanan tulee olla linkki alkuperäiseen kritiikkiin.
7.  **Suoritus:** Skriptin tulee olla ajettavissa komentoriviltä, ja se on tarkoitus ajaa 1-2 kertaa päivässä.

### Ei-toiminnalliset vaatimukset
1.  **Testattavuus:** Kaikki logiikka tulee olla yksikkötestattua.
2.  **Kehitysprosessi:** Projektissa noudatetaan testivetoista kehitystä (TDD): ensin kirjoitetaan epäonnistuva testi, sitten koodi joka läpäisee testin.
3.  **Ympäristö:** Kehitys tapahtuu lokaalisti, mutta lopullinen sovellus ajetaan LAMP VPS -palvelimella.
4.  **Integraatio:** Lopputulos (HTML-taulukko) upotetaan WordPress-sivustolle.

## 2. Teknologiat

*   **Ohjelmointikieli:** Python 3.x
*   **Kirjastot:**
    *   `requests`: HTTP-pyynnöt web-sivujen lataamiseen ja Ollama-APIn kutsumiseen.
    *   `BeautifulSoup4`: HTML-jäsentämiseen ja datan ekstraktointiin.
    *   `mysql-connector-python`: Yhteys MySQL-tietokantaan.
    *   `pytest`: Yksikkötestaukseen.
*   **Tietokanta:** MySQL
*   **Tekoälymalli:** Paikallisesti ajettava Ollama-instanssi.

## 3. Tietorakenteet ja Tietokannan Skeema

### Loogiset tietorakenteet (Python-luokat)

```python
class Critic:
    id: int
    name: str
    profile_image_url: str | None
    source_website: str # Mistä lähteestä kriitikko on (esim. 'esimerkki.fi')

class Movie:
    id: int
    normalized_title: str

class Review:
    id: int
    movie: Movie
    critic: Critic
    rating_stars: int # Arvosana (1-5)
    review_text: str | None
    source_url: str # Linkki alkuperäiseen arvosteluun
```

### Tietokannan skeema (MySQL)

```sql
CREATE TABLE critics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    profile_image_url VARCHAR(2048),
    source_website VARCHAR(255) NOT NULL,
    UNIQUE(name, source_website)
);

CREATE TABLE movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    normalized_title VARCHAR(255) NOT NULL UNIQUE
);

-- Linkkitaulu elokuvan eri nimille
CREATE TABLE movie_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    alias_title VARCHAR(255) NOT NULL UNIQUE,
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);

CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    critic_id INT NOT NULL,
    rating_stars INT NOT NULL,
    review_text TEXT,
    source_url VARCHAR(2048) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (critic_id) REFERENCES critics(id)
);
```

## 4. Komponenttien logiikka

1.  **`scraper.py` (Web Scraper)**
    *   Saa syötteenä listan konfiguraatioita eri sivustoille.
    *   Jokainen konfiguraatio määrittelee, miten (millä CSS-valitsimilla) kyseiseltä sivulta löydetään arvostelulistaukset ja yksittäisestä arvostelusta tarvittavat tiedot.
    *   Palauttaa listan raaka-dataa (sanakirjoja), jotka sisältävät löydetyt tiedot.
    *   **TDD:** Testataan paikallisilla HTML-tiedostoilla, ei live-verkkoyhteydellä.

2.  **`normalizer.py` (Datan Normalisoija)**
    *   Sisältää `normalize_movie_title(title: str) -> str` -funktion.
    *   Logiikka: muuttaa pieniksi kirjaimiksi, poistaa erikoismerkit ja mahdolliset vuosiluvut suluissa. Esim. "Dune: Part Two (2024)" -> "dune part two".
    *   **TDD:** Testataan laajalla kirjolla erilaisia syötteitä.

3.  **`rating_generator.py` (Arvosanan Generaattori)**
    *   Sisältää `generate_rating(text: str) -> int` -funktion.
    *   Lähettää arvostelutekstin HTTP POST -pyynnöllä Ollama-palvelun API-päätepisteeseen.
    *   Promptina pyydetään palauttamaan vain numero 1-5.
    *   Käsittelee vastauksen ja palauttaa kokonaisluvun.
    *   **TDD:** Testataan pilkkaamalla (mocking) `requests.post`-kutsua, jotta vältetään riippuvuus oikeasta Ollama-palvelusta testien aikana.

4.  **`database.py` (Tietokannan Hallinta)**
    *   Sisältää funktiot datan tallentamiseen ja hakemiseen.
    *   `get_or_create_movie(title: str) -> Movie`: Hakee normalisoidun elokuvan tai luo uuden. Hallinnoi myös `movie_aliases`-taulua.
    *   `get_or_create_critic(name: str, source: str) -> Critic`: Hakee tai luo kriitikon.
    *   `save_review(review_data: dict)`: Tallenataa arvostelun. Varmistaa, ettei samaa `source_url`-osoitetta tallenneta kahdesti.

5.  **`html_generator.py` (HTML-Generaattori)**
    *   Hakee kaiken datan tietokannasta.
    *   Rakentaa datan perusteella pivot-taulukon (elokuvat riveillä, kriitikot sarakkeissa).
    *   Kirjoittaa lopputuloksen `kritiikit.html`-tiedostoon.

6.  **`main.py` (Pääohjelma)**
    *   Orkestroi koko prosessin:
        1.  Kutsuu `scraper.py`:tä hakemaan raakadata.
        2.  Kiertää datan läpi:
            a. Jos arvosana puuttuu, kutsuu `rating_generator.py`:tä.
            b. Normalisoi elokuvan nimen `normalizer.py`:llä.
            c. Tallentaa kaiken tietokantaan `database.py`:n avulla.
        3.  Lopuksi kutsuu `html_generator.py`:tä luomaan lopullisen HTML-sivun.
