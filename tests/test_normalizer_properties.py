"""Bounded, replayable title-normalization properties (no network or database)."""
import os
import random
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from movie_normalizer import normalize_movie_title, similarity_ratio, find_matching_movie

SEED = int(os.environ.get("FUZZ_SEED", "20261106"))


@pytest.mark.parametrize("seed", [SEED, SEED + 1, SEED + 2])
def test_title_normalization_properties(seed):
    rng = random.Random(seed)
    alphabet = "AbcXYZäöåÉ中012_ -,:.!?()\t\n\r\x00😀"
    for case in range(120):
        title = "".join(rng.choices(alphabet, k=rng.randrange(0, 100)))
        normalized = normalize_movie_title(title)
        context = f"seed={seed} case={case} title={title!r}"
        assert normalized == normalize_movie_title(normalized), context
        assert normalized == normalized.strip(), context
        assert not re.search(r"[^\w\s]|\s{2,}", normalized), context
        assert 0 <= similarity_ratio(title, title[::-1]) <= 1, context
        if normalized:
            assert similarity_ratio(title, normalized) == 1, context
            assert find_matching_movie(title, [normalized], threshold=1) == normalized, context


@pytest.mark.parametrize("seed", [SEED, SEED + 1])
def test_parenthetical_alias_does_not_erase_primary_title(seed):
    rng = random.Random(seed)
    for case in range(100):
        primary = "Elokuva " + str(rng.randrange(100000))
        alias = "English title " + str(rng.randrange(100000))
        title = f"{primary} ({alias})"
        context = f"seed={seed} case={case} title={title!r}"
        assert normalize_movie_title(title, strip_parentheses=True) == primary.lower(), context
        assert similarity_ratio(title, primary) == 1, context


def test_whitespace_regression_fixture():
    # Minimal retained input for the deliberate whitespace-collapse mutant.
    assert normalize_movie_title("A\t \nB") == "a b"
