#!/bin/bash
set -e

# Configuration
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
SRC_DIR="$PROJECT_DIR/src"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting publish process...${NC}"

# 1. Activate venv
if [ -f "$VENV_ACTIVATE" ]; then
    echo "📦 Activating virtual environment..."
    source "$VENV_ACTIVATE"
else
    echo -e "${RED}❌ Virtual environment not found at $VENV_ACTIVATE${NC}"
    exit 1
fi

# 2. Run tests
echo "🧪 Running tests..."
export PYTHONPATH="$SRC_DIR"
if python3 -m pytest tests/ -q; then
    echo -e "${GREEN}✅ Tests passed.${NC}"
else
    echo -e "${RED}❌ Tests failed. Aborting.${NC}"
    exit 1
fi

# 3. Run scrapers
echo "🕷️ Running scrapers (limit=5)..."
# Use batch_update.py logic
if python3 "$SRC_DIR/batch_update.py"; then
    echo -e "${GREEN}✅ Scrapers finished.${NC}"
else
    echo -e "${RED}❌ Scrapers failed. Aborting.${NC}"
    exit 1
fi

# 4. Generate static site
echo "📄 Generating static site..."
if python3 "$PROJECT_DIR/scripts/generate_static.py"; then
    echo -e "${GREEN}✅ Static site generated.${NC}"
else
    echo -e "${RED}❌ Site generation failed. Aborting.${NC}"
    exit 1
fi

# 5. Git Push
echo "📤 Pushing to GitHub..."
git add docs/ reviews.db
TS=$(date +"%Y-%m-%d %H:%M:%S")
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    git commit -m "Manual update: $TS"
    git push
    echo -e "${GREEN}✅ Changes pushed to GitHub.${NC}"
fi

echo -e "${GREEN}🎉 Done!${NC}"
