# Changelog

Kaikki merkittävät muutokset projektiin dokumentoidaan tähän.

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
