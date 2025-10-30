#!/usr/bin/env python3
"""
Eräajo-scripti - Päivittää tietokannan säännöllisesti.

Käyttö:
    python3 batch_update.py                # Importoi kaikista lähteistä 5 arvostelua
    python3 batch_update.py --limit 10     # Importoi 10 arvostelua per lähde
    python3 batch_update.py --source hs    # Importoi vain HS:stä
    python3 batch_update.py --full         # Täysi päivitys (20 arvostelua per lähde)

Cron-esimerkki (päivittää joka päivä klo 08:00):
    0 8 * * * cd /path/to/kriitikot/src && python3 batch_update.py >> /var/log/kriitikot.log 2>&1
"""

import argparse
import sys
from datetime import datetime
from discovery_importer import DiscoveryImporter


def main():
    parser = argparse.ArgumentParser(
        description='Päivittää kriitikot-tietokannan uusilla arvosteluilla'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='Montako arvostelua per lähde (oletus: 5)'
    )
    parser.add_argument(
        '--source',
        type=str,
        choices=['hs', 'ts', 'il', 'ksml', 'sk', 'all'],
        default='all',
        help='Lähde josta importoidaan (oletus: all)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Täysi päivitys (20 arvostelua per lähde)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Tulosta yksityiskohtainen loki'
    )
    
    args = parser.parse_args()
    
    # Määritä limit
    limit = 20 if args.full else args.limit
    
    # Tulosta aloitusviesti
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*70}")
    print(f"🤖 ERÄAJO - Kriitikot-tietokannan päivitys")
    print(f"{'='*70}")
    print(f"⏰ Aika: {timestamp}")
    print(f"📊 Asetukset:")
    print(f"   - Lähde: {args.source}")
    print(f"   - Limit per lähde: {limit}")
    print(f"   - Verbose: {args.verbose}")
    print(f"{'='*70}\n")
    
    try:
        # Luo importer
        importer = DiscoveryImporter()
        
        # Importoi
        if args.source == 'all':
            results = importer.import_all_sources(limit_per_source=limit)
            total_imported = sum(results.values())
        else:
            total_imported = importer.import_discovered_reviews(args.source, limit)
        
        # Yhteenveto
        print(f"\n{'='*70}")
        print(f"✅ ERÄAJO VALMIS")
        print(f"{'='*70}")
        print(f"📈 Importoitu yhteensä: {total_imported} arvostelua")
        print(f"⏰ Päättyi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        # Exit code: onnistui
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Keskeytetty käyttäjän toimesta")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n\n❌ VIRHE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
