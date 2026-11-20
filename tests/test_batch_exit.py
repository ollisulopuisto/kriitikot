"""A partial scraper run must not publish as a successful update."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

def test_batch_nonzero_exit_when_one_source_fails(monkeypatch):
    import batch_update
    importer = SimpleNamespace(source_failures={'is': 2}, import_all_sources=lambda **k: {'is': 0, 'hs': 1})
    monkeypatch.setattr(batch_update,'DiscoveryImporter',lambda:importer)
    monkeypatch.setattr(sys,'argv',['batch_update.py'])
    import pytest
    with pytest.raises(SystemExit) as exit:
        batch_update.main()
    assert exit.value.code == 1

