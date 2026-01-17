import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scrapers.hs import HSScraper


def test_normalize_critic_name_examples():
    s = HSScraper()

    cases = {
        'Mikko-Pekka Heikkinen HS': 'Mikko-Pekka Heikkinen',
        'Mikko-Pekka Heikkinen, HS': 'Mikko-Pekka Heikkinen',
        'Mikko-Pekka Heikkinen Helsingin Sanomat': 'Mikko-Pekka Heikkinen',
        'Mikko-Pekka Heikkinen, Helsingin Sanomat': 'Mikko-Pekka Heikkinen',
        'Anna Virtanen': 'Anna Virtanen',
        # If input is only the publication marker, normalization should fall back to original
        'HS': 'HS',
    }

    for inp, expected in cases.items():
        got = s._normalize_critic_name(inp)
        assert got == expected, f"normalize('{inp}') -> '{got}', expected '{expected}'"

