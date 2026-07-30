"""Testit RSS-syötteen aikaleimoille.

Kanta tallentaa naiiveja UTC-aikoja. datetime.timestamp() tulkitsee naiivin
ajan paikalliseksi, joten ilman nimenomaista UTC-merkintää syötteen päiväykset
siirtyivät generoivan koneen aikavyöhykkeen verran: Helsingissä ajettu
generointi tuotti 3 tuntia CI:n tuloksesta poikkeavat ajat, ja tiedosto
heilui edestakaisin joka committiin.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import rfc2822


def test_naive_datetime_is_treated_as_utc():
    assert rfc2822(datetime(2026, 7, 30, 8, 31, 18)) == 'Thu, 30 Jul 2026 08:31:18 -0000'


def test_aware_utc_datetime_is_unchanged():
    aware = datetime(2026, 7, 30, 8, 31, 18, tzinfo=timezone.utc)
    assert rfc2822(aware) == 'Thu, 30 Jul 2026 08:31:18 -0000'


def test_naive_and_aware_agree():
    naive = datetime(2026, 1, 15, 12, 0, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert rfc2822(naive) == rfc2822(aware)


def test_output_is_independent_of_local_timezone():
    """Sama aikaleima tuottaa saman merkkijonon riippumatta TZ-ympäristömuuttujasta."""
    import time

    stamp = datetime(2026, 7, 30, 8, 31, 18)
    original = os.environ.get('TZ')
    results = []
    try:
        for tz in ('UTC', 'Europe/Helsinki', 'America/Los_Angeles'):
            os.environ['TZ'] = tz
            time.tzset()
            results.append(rfc2822(stamp))
    finally:
        if original is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = original
        time.tzset()

    assert len(set(results)) == 1, f'aikavyöhyke vaikutti tulokseen: {results}'
