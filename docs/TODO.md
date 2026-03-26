# Puuttuvia scrapereita
- episodi
    - tästä on JSONia https://www.episodi.fi/wp-json/wp/v2/elokuvat ja https://www.episodi.fi/wp-json/wp/v2/kirjoittajat/1790
- muropaketti
    - kaikki arviot https://muropaketti.com/kategoria/elokuvat/elokuva-arvostelut/
    - yksittäinen arvio https://muropaketti.com/elokuvat/elokuva-arvostelut/arvostelu-kalju-emma-stone-kannattelee-bugoniaa-mutta-ohjaaja-yorgos-lanthimosin-on-pakko-keksia-elokuviinsa-jo-jotain-uutta/
- film-o-holic
    - kaikki arviot https://www.film-o-holic.com/arvostelut/
    - yksittäinen arvio https://www.film-o-holic.com/arvostelut/sorry-baby/
- kulttuuritoimitus
    - kaikki arviot https://kulttuuritoimitus.fi/kritiikit/kritiikit-elokuva/
    - yksittäinen arvio https://kulttuuritoimitus.fi/kritiikit/kritiikit-elokuva/yorgos-lanthimos-kuvaa-nykymaailman-hulluutta-osuvasti-mutta-rankasti-arviossa-ensi-iltaelokuva-bugonia/
- karjalainen / savon sanomat 
- kaleva: EI TÄHTIÄ ARVIOISSA
    - kaikki arviot https://www.kaleva.fi/aihe/elokuvat/286 etsi avainsana "arvio"
    - yksittäinen arvio https://www.kaleva.fi/arvio-terapeutin-pojalla-on-pelottava-heila-kotima/12375327


# Toiminnallisuus
- 🎬 **Kriitikon valinta (Desktop/Mobile) - FIX IN PROGRESS**
    - **Nykytila:** Kriitikon nimen klikkaaminen headerissa (desktop) asettaa `dataset.filtered = 'true'`, mutta ei päivitä sarakkeiden näkyvyyttä taulukossa. Mobiili-näkymän kortit päivittyvät osittain, mutta logiikka on hajallaan.
    - **Havainnot:** `static/interactions.js`:n `window.filterByCritic` ei kutsu `updateCriticColumnVisibility()` -funktiota (tahallaan tai vahingossa), jolloin taulukon sarakkeet eivät piiloudu.
    - **Seuraavat askeleet:**
        1. Lisää debug-logit `filterByCritic` ja `updateCriticColumnVisibility` -funktioihin.
        2. Varmista, että `filterByCritic` kutsuu `updateCriticColumnVisibility()` ja että se käsittelee `selectedCriticHeader` -tapauksen oikein.
        3. Yhdenmukaista mobiili- ja desktop-suodatuslogiikka niin, että molemmat käyttävät samaa `dataset.filtered` -tilaa ja triggeröivät samat päivitykset.
        4. Testaa "Reset"-painikkeen toiminta suodatuksen jälkeen.
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