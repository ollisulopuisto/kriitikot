#!/bin/bash
# Kriitikot eräajo-wrapper
# Käyttö: ./run_batch_update.sh [daily|weekly|hourly]

set -e  # Lopeta jos tulee virhe

# Määritä absoluuttiset polut
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$SCRIPT_DIR/batch_update.py"
LOG_DIR="$PROJECT_DIR/logs"
DB_BACKUP_DIR="$PROJECT_DIR/backups"

# Luo hakemistot jos eivät ole olemassa
mkdir -p "$LOG_DIR"
mkdir -p "$DB_BACKUP_DIR"

# Tiedostonimet päivämäärällä
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/batch_update_$TIMESTAMP.log"
DB_FILE="$PROJECT_DIR/reviews.db"
BACKUP_FILE="$DB_BACKUP_DIR/reviews_$TIMESTAMP.db"

# Määritä tyyppi (daily, weekly, hourly)
UPDATE_TYPE="${1:-daily}"

echo "================================================" | tee -a "$LOG_FILE"
echo "Kriitikot Eräajo - $UPDATE_TYPE" | tee -a "$LOG_FILE"
echo "Aika: $(date)" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

# Backup tietokannasta
if [ -f "$DB_FILE" ]; then
    echo "📦 Luodaan backup: $BACKUP_FILE" | tee -a "$LOG_FILE"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Poista yli 7 päivää vanhat backupit
    find "$DB_BACKUP_DIR" -name "reviews_*.db" -mtime +7 -delete
else
    echo "⚠️  Tietokantaa ei löydy: $DB_FILE" | tee -a "$LOG_FILE"
fi

# Määritä limit tyypin mukaan
case $UPDATE_TYPE in
    hourly)
        LIMIT=3
        ;;
    daily)
        LIMIT=10
        ;;
    weekly)
        LIMIT=20
        ;;
    *)
        LIMIT=5
        ;;
esac

# Aja päivitys
echo "🚀 Ajetaan päivitys (limit: $LIMIT)..." | tee -a "$LOG_FILE"
cd "$SCRIPT_DIR"

if python3 "$PYTHON_SCRIPT" --limit "$LIMIT" >> "$LOG_FILE" 2>&1; then
    echo "✅ Päivitys onnistui!" | tee -a "$LOG_FILE"
    EXIT_CODE=0
else
    echo "❌ Päivitys epäonnistui!" | tee -a "$LOG_FILE"
    EXIT_CODE=1
fi

# Poista yli 30 päivää vanhat logit
find "$LOG_DIR" -name "batch_update_*.log" -mtime +30 -delete

echo "================================================" | tee -a "$LOG_FILE"
echo "Loki tallennettu: $LOG_FILE"
echo "================================================"

exit $EXIT_CODE
