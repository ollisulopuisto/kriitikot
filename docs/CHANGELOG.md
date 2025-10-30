# Changelog

Kaikki merkittävät muutokset projektiin dokumentoidaan tähän.

## [0.4.0] - 2025-10-30

### ✨ Lisätty
- **TS-scraper (Turun Sanomat)**
  - `TSScraper`: Parsii TS.fi:n arvostelut
  - Tuki maksumuurin takana oleville arvosteluille (curl + oikeat headerit)
  - ★-symbolipohjainen tähtiarvioiden poiminta
  - Meta property="article:author" -parsinta
  - JSON-LD structured data -tuki
  
- **Testit**
  - 10 automaattista testiä (HS: 4, KSML: 2, IL: 2, TS: 2)
  - Testidata kaikille neljälle lähteelle

### 🔧 Parannettu
- `scrape_review()` tukee nyt neljää lähdettä: 'hs', 'ksml', 'il', 'ts'
- Esimerkkiskripti päivitetty (examples.py): TS-esimerkki tulossa
- README.md päivitetty: 4 lähdettä dokumentoitu

## [0.3.0] - 2025-10-30

### ✨ Lisätty
- **KSML-scraper (Keskisuomalainen)**
  - `KSMLScraper`: Parsii KSML.fi:n arvostelut
  - Tuki maksumuurin takana oleville arvosteluille
  - Aria-label -pohjainen tähtiarvioiden poiminta
  - JSON-LD structured data -parsinta
  
- **IL-scraper (Iltalehti)**
  - `ILScraper`: Parsii Iltalehti.fi:n arvostelut
  - Tuki ⭐-symbolipohjaisille arvosteluille (regex: `IL-arvio: ⭐⭐`)
  - Automaattinen aikaleiman poisto kirjoittajan nimestä
  
- **Testit**
  - 8 automaattista testiä (HS: 4, KSML: 2, IL: 2)
  - Testidata kaikille kolmelle lähteelle

### 🔧 Parannettu
- `scrape_review()` tukee nyt kolmea lähdettä: 'hs', 'ksml', 'il'
- Esimerkkiskripti päivitetty (examples.py): KSML + IL esimerkit
- README.md päivitetty: 3 lähdettä dokumentoitu

## [0.2.0] - 2025-10-30

### ✨ Lisätty
- **Modulaarinen scraper-arkkitehtuuri**
  - `Review`-luokka: Yhtenäinen tietorakenne kaikille arvosteluille
  - `HSScraper`: Helsingin Sanomien arvostelujen parsija
  - `scrape_review()`: Yleinen funktio joka tukee useita lähteitä
  
- **Web-sovellus (Flask)**
  - Graafinen käyttöliittymä arvostelujen katseluun
  - Responsiivinen design
  - JSON REST API

- **Dokumentaatio**
  - Kattava README.md
  - Esimerkkiskripti (`examples.py`)
  - Quick start -skripti (`quickstart.sh`)
  - Inline-dokumentaatio koodissa

- **Testaus**
  - 4 automaattista testiä scraperille
  - Testit käyttävät oikeaa HS-arvostelua

### 🔧 Parannettu
- Tähtiarvioiden parsinta toimii nyt oikein (löytää `content`-kentästä)
- Elokuvan nimien parsinta (poistaa prefix-tekstit)
- Kriitikon nimen ja julkaisun tietojen poiminta

### 🎯 Arkkitehtuuriset päätökset
- **Ei kovakoodattuja oletuksia**: Kaikki on parametrisoitu
- **Helppo laajentaa**: Uuden lähteen lisääminen vaatii vain uuden scraper-luokan
- **Testattavuus**: TDD-lähestymistapa, testit ensin
- **Selkeät rajapinnat**: Review-luokka abstrahoi erot lähteiden välillä

## [0.1.0] - 2025-XX-XX

### ✨ Lisätty
- Alkuperäinen prototyyppi
- Perus HS-scraper (raakile)
- Projektirakenteen perusteet
- SUUNNITELMA.md
