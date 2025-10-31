# Puuttuvia scrapereita
- episodi
    - tästä on JSONia https://www.episodi.fi/wp-json/wp/v2/elokuvat ja https://www.episodi.fi/wp-json/wp/v2/kirjoittajat/1790
- muropaketti
- kaleva
- film-o-holic
- karjalainen / savon sanomat 

# Toiminnallisuus
- elokuvan tiedot -leiska, mihin se laitetaan desktopissa? mobiilissa helpompi, kun on jo kortit
    - lippujen ostamista varten linkit TMDB, nytleffaan.fi
    - elokuvan juliste
    - linkki letterboxd
- ✅ erotetaan arvioiden scraping ja niiden julkaiseminen saitilla: jätetään skreipatut arviot ensin pending-tilaan, näytetään ne listana admin-sivulla ja odotetaan että admin hyväksyy julkaisun
    - ✅ näin voi muokata ensin otsikon korrektiksi jne.
    - ✅ Admin-sivu näyttää pending-arviot
    - ✅ Julkaise/Poista -painikkeet pending-arvioille
    - ✅ Checkbox julkaistuille arvioille - mahdollistaa piilottamisen frontendistä

# Tietomalli
- ✅ milloin arvio on julkaistu (published_date kenttä Reviews-taulussa)
- ⚠️ linkki nytleffaan.fi (tietokantakenttä olemassa, ei vielä käytössä)
- ✅ linkki imdb.org (imdb_id kenttä Movies-taulussa)
- ✅ kuva tmdb.org:ista ladattuna (poster_url kenttä Movies-taulussa)
- ✅ tieto siitä, onko arvio julkaistu saitilla (is_published kenttä Reviews-taulussa)
- ✅ TMDB ID (tmdb_id kenttä Movies-taulussa)
- ✅ Letterboxd URL (letterboxd_url kenttä Movies-taulussa)