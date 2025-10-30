#!/usr/bin/env python3
"""
Quick Import - Nopea importti kaikista lähteistä testaustarkoituksiin.

Tämä scripti on hyödyllinen kun haluat nopeasti testata että kaikki toimii.
"""

from discovery_importer import DiscoveryImporter
import sys


def main():
    print("\n" + "="*60)
    print("⚡ QUICK IMPORT - Nopea testi")
    print("="*60 + "\n")
    print("Importoidaan 2 arvostelua jokaisesta lähteestä...")
    print("(Ohittaa duplikaatit automaattisesti)\n")
    
    importer = DiscoveryImporter()
    
    # Importoi 2 arvostelua per lähde
    results = importer.import_all_sources(limit_per_source=2)
    
    total = sum(results.values())
    
    if total == 0:
        print("\n⚠️  Kaikki arvostelut olivat jo tietokannassa!")
        print("💡 Kokeile suurempaa limittiä tai poista vanhoja arvosteluja.\n")
        return 1
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Keskeytetty\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Virhe: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
