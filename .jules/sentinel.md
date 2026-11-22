# Sentinel's Journal - kriitikot

## 2026-11-01 - Ulkoisen datan escaappaus client-renderöinnissä
**Learning:** Kun data tulee ulkoisista lähteistä ja renderöidään template-literaaleilla selaimessa, palvelinpuolen autoescape ei kata sitä. Client-renderöintipolku tarvitsee oman escaappauksensa ja URL-validointinsa.
**Prevention:** escapeHtml() kaikkiin data-interpolointeihin, safeHttpUrl() linkki- ja kuva-attribuutteihin, regressiotestit tests/frontend/xss-escaping.test.js. Tarkista aina sekä palvelin- että client-renderöintipolut.
