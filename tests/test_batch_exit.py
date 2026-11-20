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
    assert exit.value.code == 2


def test_fatal_batch_error_remains_exit_one(monkeypatch):
    import batch_update,pytest
    def fatal():
        raise RuntimeError('database unavailable')
    monkeypatch.setattr(batch_update,'DiscoveryImporter',fatal)
    monkeypatch.setattr(sys,'argv',['batch_update.py'])
    with pytest.raises(SystemExit) as exit:
        batch_update.main()
    assert exit.value.code==1


def test_workflow_uses_single_successful_commit_path_and_reports_partial_failure():
    workflow=(Path(__file__).parents[1]/'.github/workflows/scrape_and_deploy.yml').read_text(encoding='utf-8')
    assert workflow.count('git push origin HEAD:main')==1
    assert 'if: always()' not in workflow
    assert 'if [ "$status" -eq 2 ]' in workflow
    assert 'elif [ "$status" -ne 0 ]; then\n            exit "$status"' in workflow
    assert workflow.index('Stop publication after failed tests')<workflow.index('Run scrapers (batch update)')
    assert workflow.index('Commit & push changes')<workflow.index('Report source failures after publication')<workflow.index('Create issue on job failure')
    assert 'GITHUB_STEP_SUMMARY' in workflow
    assert 'git add docs reviews.db || true' not in workflow


def test_scrape_shell_only_allows_completed_partial_results(tmp_path):
    import subprocess,os
    workflow=(Path(__file__).parents[1]/'.github/workflows/scrape_and_deploy.yml').read_text(encoding='utf-8')
    step=workflow.split('      - name: Run scrapers (batch update)',1)[1].split('      - name: Backfill',1)[0]
    shell=step.split('        run: |\n',1)[1]
    shell='\n'.join(line[10:] for line in shell.splitlines())
    executable=tmp_path/'uv'
    executable.write_text('#!/bin/sh\nexit "$TEST_STATUS"\n',encoding='utf-8');executable.chmod(0o755)
    for status,expected,partial in [(0,0,False),(2,0,True),(1,1,False),(130,130,False)]:
        envfile=tmp_path/f'env{status}';summary=tmp_path/f'summary{status}'
        envfile.touch();summary.touch()
        result=subprocess.run(['bash','-e','-c',shell],env={**os.environ,'PATH':str(tmp_path)+':'+os.environ['PATH'],'TEST_STATUS':str(status),'GITHUB_ENV':str(envfile),'GITHUB_STEP_SUMMARY':str(summary)},capture_output=True,text=True)
        assert result.returncode==expected,result.stderr
        assert ('PARTIAL_SCRAPE=1' in envfile.read_text(encoding='utf-8'))==partial
