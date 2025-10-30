# Kriitikot - Eräajojen asennus

## Vaihtoehto 1: Cron (yksinkertaisin)

### Päivittäinen päivitys klo 08:00

```bash
# Muokkaa crontab:
crontab -e

# Lisää rivi:
0 8 * * * cd /workspaces/kriitikot/src && /usr/bin/python3 batch_update.py >> /var/log/kriitikot.log 2>&1
```

### Päivitys 3 kertaa päivässä (08:00, 14:00, 20:00)

```bash
0 8,14,20 * * * cd /workspaces/kriitikot/src && /usr/bin/python3 batch_update.py >> /var/log/kriitikot.log 2>&1
```

### Täysi päivitys viikonloppuisin klo 10:00

```bash
0 10 * * 0,6 cd /workspaces/kriitikot/src && /usr/bin/python3 batch_update.py --full >> /var/log/kriitikot.log 2>&1
```

## Vaihtoehto 2: Systemd Timer (edistyneempi)

### 1. Luo service-tiedosto

```bash
sudo nano /etc/systemd/system/kriitikot-update.service
```

Sisältö:
```ini
[Unit]
Description=Kriitikot Database Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=YOUR_USERNAME
WorkingDirectory=/workspaces/kriitikot/src
ExecStart=/usr/bin/python3 batch_update.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Luo timer-tiedosto

```bash
sudo nano /etc/systemd/system/kriitikot-update.timer
```

Sisältö (päivittäin klo 08:00):
```ini
[Unit]
Description=Kriitikot Database Update Timer
Requires=kriitikot-update.service

[Timer]
OnCalendar=daily
# Tai tarkemmin:
# OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. Aktivoi timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable kriitikot-update.timer
sudo systemctl start kriitikot-update.timer
```

### 4. Tarkista status

```bash
# Katso timer-status
systemctl status kriitikot-update.timer

# Katso lokit
journalctl -u kriitikot-update.service -f
```

## Vaihtoehto 3: Docker Cron

Jos käytät Dockeria, lisää `.devcontainer/devcontainer.json`:

```json
{
  "postCreateCommand": "crontab -l | { cat; echo '0 8 * * * cd /workspaces/kriitikot/src && /usr/bin/python3 batch_update.py'; } | crontab -"
}
```

## Manuaalinen käyttö

```bash
# Perus käyttö (kaikki lähteet, 5 arvostelua)
cd /workspaces/kriitikot/src
python3 batch_update.py

# Vain HS.fi, 10 arvostelua
python3 batch_update.py --source hs --limit 10

# Täysi päivitys (20 arvostelua per lähde)
python3 batch_update.py --full

# Yksityiskohtainen loki
python3 batch_update.py --verbose
```

## Lokit

Cron-lokit tallentuvat määriteltyyn tiedostoon:
```bash
tail -f /var/log/kriitikot.log
```

Systemd-lokit katsotaan journalctl:lla:
```bash
journalctl -u kriitikot-update.service --since today
```

## Tietokanta-backup

Suositus: Ota tietokannasta varmuuskopio ennen eräajoja:

```bash
# SQLite-backup
sqlite3 /workspaces/kriitikot/reviews.db ".backup /backups/reviews_$(date +%Y%m%d).db"
```

Lisää crontab:iin ennen update-riviä:
```bash
# Backup klo 07:55
55 7 * * * sqlite3 /workspaces/kriitikot/reviews.db ".backup /backups/reviews_$(date +\%Y\%m\%d).db"
# Update klo 08:00
0 8 * * * cd /workspaces/kriitikot/src && /usr/bin/python3 batch_update.py >> /var/log/kriitikot.log 2>&1
```
