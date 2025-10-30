#!/bin/bash

# Quick start -skripti Elokuvakritiikkien Kerääjälle

echo "🎬 Elokuvakritiikkien Kerääjä - Pika-aloitus"
echo "=============================================="
echo ""

# 1. Tarkista Python
echo "1️⃣  Tarkistetaan Python-asennus..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 ei löydy! Asenna Python 3.9 tai uudempi."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION löytyi"
echo ""

# 2. Asenna riippuvuudet
echo "2️⃣  Asennetaan riippuvuudet..."
pip3 install -q -r requirements.txt
echo "✅ Riippuvuudet asennettu"
echo ""

# 3. Aja testit
echo "3️⃣  Ajetaan testit..."
python3 -m pytest tests/test_scraper.py -v --tb=short
if [ $? -eq 0 ]; then
    echo "✅ Kaikki testit läpäisty!"
else
    echo "⚠️  Jotkut testit epäonnistuivat"
fi
echo ""

# 4. Näytä esimerkkejä
echo "4️⃣  Ajetaan esimerkit..."
cd src && PYTHONPATH=/workspaces/kriitikot/src python3 examples.py
cd ..
echo ""

# 5. Ohje sovelluksen käynnistämiseen
echo "=============================================="
echo "✅ Asennus valmis!"
echo ""
echo "🚀 Käynnistä web-sovellus:"
echo "   python3 src/app.py"
echo ""
echo "🌐 Avaa selaimessa:"
echo "   http://localhost:5000"
echo ""
echo "🧪 Aja testit:"
echo "   pytest tests/ -v"
echo ""
echo "📚 Lue lisää: README.md"
echo "=============================================="
