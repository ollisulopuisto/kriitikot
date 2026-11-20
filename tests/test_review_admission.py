"""Incomplete discovered reviews must never look like successful no-op imports."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from discovery_importer import DiscoveryImporter
from models import Base,get_session,Publication,Movie,Critic,Review
from sqlalchemy import create_engine


@pytest.mark.parametrize('field,value',[
    ('movie_title',None),('movie_title',' '),('critic_name',None),('critic_name','Unknown'),
    ('critic_name','Turun Sanomat'),('critic_name','https://example.test/author'),
    ('rating_stars',None),('rating_stars',0),('rating_stars',6),('rating_stars',3.5),('rating_stars',True)])
def test_invalid_identity_is_failure_not_a_silent_skip(monkeypatch,field,value):
    import discovery_importer
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine);db=get_session(engine)
    db.add(Publication(name='Turun Sanomat',short_name='ts'));db.commit()
    importer=DiscoveryImporter.__new__(DiscoveryImporter);importer.session=db;importer.source_failures={}
    importer.meta_scraper=SimpleNamespace(discover_new_reviews=lambda *a:[{'title':'Article','url':'https://example.test/review'}])
    fields={'movie_title':'A Film','critic_name':'A Critic','rating_stars':3,
            'source_url':'https://example.test/review','review_text':'Review'};fields[field]=value
    importer.scrapers={'ts':SimpleNamespace(parse_html=lambda *a:SimpleNamespace(**fields))}
    importer.get_or_create_movie=MagicMock(side_effect=AssertionError('Must not create a movie'))
    importer.get_or_create_critic=MagicMock(side_effect=AssertionError('Must not create a critic'))
    monkeypatch.setattr(discovery_importer.requests,'get',lambda *a,**k:SimpleNamespace(text='fixture',raise_for_status=lambda:None))
    assert importer.import_discovered_reviews('ts')==0
    assert importer.source_failures=={'ts':1}
    importer.get_or_create_movie.assert_not_called();importer.get_or_create_critic.assert_not_called()
    assert db.query(Movie).count()==db.query(Critic).count()==db.query(Review).count()==0
