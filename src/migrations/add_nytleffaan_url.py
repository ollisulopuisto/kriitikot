#!/usr/bin/env python3
"""
Migraatio: Lisää nytleffaan.fi-linkki Movies-tauluun.
"""

import sqlite3
import os
import sys

# Lisää src-hakemisto polkuun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate_database(db_path='../../reviews.db'):
    """Päivittää tietokannan lisäämällä nytleffaan_url kentän."""
    
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
        # Lisää nytleffaan_url kenttä Movies-tauluun
        print("Lisätään nytleffaan_url kenttä Movies-tauluun...")
        
        try:
            cursor.execute("ALTER TABLE movies ADD COLUMN nytleffaan_url VARCHAR(500)")
            print("  ✓ Lisätty: movies.nytleffaan_url")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("  - Ohitetaan: movies.nytleffaan_url (on jo olemassa)")
            else:
                raise
        
        conn.commit()
        print("✅ Migraatio onnistui!")
        
        # Näytä Movies-taulun rakenne
        print("\n=== Movies-taulun rakenne ===")
        cursor.execute("PRAGMA table_info(movies)")
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
    
    parser = argparse.ArgumentParser(description='Lisää nytleffaan_url kentän Movies-tauluun')
    parser.add_argument('--db', default='../../reviews.db', help='Tietokantatiedoston polku')
    
    args = parser.parse_args()
    
    success = migrate_database(args.db)
    sys.exit(0 if success else 1)