#!/usr/bin/env python3
"""
Migraatio: Lisää elokuvan metatiedot ja arvion julkaisupäivä.

Lisää Movies-tauluun:
- published_date (DateTime)
- tmdb_id (Integer)
- imdb_id (String)
- poster_url (String)
- letterboxd_url (String)

Lisää Reviews-tauluun:
- published_date (DateTime)
- is_published (Integer, 0=pending / 1=julkaistu)
"""

import sqlite3
import os
import sys

# Lisää src-hakemisto polkuun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate_database(db_path='../kriitikot.db'):
    """Päivittää tietokannan lisäämällä uudet kentät."""
    
    # Muodosta absoluuttinen polku
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(script_dir, db_path)
    
    print(f"Päivitetään tietokanta: {db_file}")
    
    if not os.path.exists(db_file):
        print(f"VIRHE: Tietokantaa ei löydy: {db_file}")
        return False
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Lisää Movies-taulun uudet kentät
        print("\nLisätään Movies-tauluun uudet kentät...")
        
        movie_columns = [
            ("published_date", "DATETIME"),
            ("tmdb_id", "INTEGER"),
            ("imdb_id", "VARCHAR(20)"),
            ("poster_url", "VARCHAR(500)"),
            ("letterboxd_url", "VARCHAR(500)")
        ]
        
        for col_name, col_type in movie_columns:
            try:
                cursor.execute(f"ALTER TABLE movies ADD COLUMN {col_name} {col_type}")
                print(f"  ✓ Lisätty: movies.{col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Ohitetaan: movies.{col_name} (on jo olemassa)")
                else:
                    raise
        
        # Lisää Reviews-taulun uudet kentät
        print("\nLisätään Reviews-tauluun uudet kentät...")
        
        review_columns = [
            ("published_date", "DATETIME"),
            ("is_published", "INTEGER DEFAULT 0 NOT NULL")
        ]
        
        for col_name, col_type in review_columns:
            try:
                cursor.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type}")
                print(f"  ✓ Lisätty: reviews.{col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Ohitetaan: reviews.{col_name} (on jo olemassa)")
                else:
                    raise
        
        conn.commit()
        
        # Aseta kaikki nykyiset arviot julkaistuiksi
        print("\nAsetetaan nykyiset arviot julkaistuiksi...")
        try:
            cursor.execute("UPDATE reviews SET is_published = 1 WHERE is_published = 0")
            updated = cursor.rowcount
            conn.commit()
            print(f"  ✓ Asetettu {updated} arvostelua julkaistuiksi")
        except Exception as e:
            print(f"  - Virhe: {e}")
        
        print("\n✅ Migraatio onnistui!")
        
        # Näytä taulujen rakenne
        print("\n=== Movies-taulun rakenne ===")
        cursor.execute("PRAGMA table_info(movies)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")
        
        print("\n=== Reviews-taulun rakenne ===")
        cursor.execute("PRAGMA table_info(reviews)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ VIRHE migraatiossa: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migroi tietokanta lisäämällä metatietokentät')
    parser.add_argument('--db', default='../kriitikot.db', help='Tietokantatiedoston polku')
    
    args = parser.parse_args()
    
    success = migrate_database(args.db)
    sys.exit(0 if success else 1)
