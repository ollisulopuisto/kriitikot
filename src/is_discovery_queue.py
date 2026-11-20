"""Persistent bounded IS queue. Cache article metadata/outcomes, never HTML."""
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import tempfile
from models import Review
from urllib.parse import urlsplit
import re


class ISDiscoveryQueue:
    def __init__(self, session, path=None, now=None):
        self.session = session
        self.path = Path(path) if path else None
        self.now = now or datetime.utcnow()
        self.rows = {}
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version') != 1 or not isinstance(data.get('articles'), dict):
                raise ValueError('Invalid IS queue cache')
            self.rows = data['articles']
            for url, row in self.rows.items():
                if (not self.valid_url(url) or not isinstance(row,dict) or
                    row.get('status') not in ('pending','failed','excluded','imported') or
                    not isinstance(row.get('title'),str) or not isinstance(row.get('sequence'),int)):
                    raise ValueError('Invalid IS queue article')
                datetime.fromisoformat(row['discovered_at'])
                if row['checked_at']:
                    datetime.fromisoformat(row['checked_at'])

    @staticmethod
    def valid_url(value):
        if not isinstance(value,str):
            return False
        try:
            parsed = urlsplit(value)
            return (parsed.scheme == 'https' and parsed.netloc == 'www.is.fi' and
                    bool(re.fullmatch(r'/tv-ja-elokuvat/art-\d+\.html',parsed.path)) and
                    not parsed.query and not parsed.fragment)
        except ValueError:
            return False

    def enqueue(self, candidates):
        imported = {url for (url,) in self.session.query(Review.source_url)}
        for i, item in enumerate(candidates):
            if not self.valid_url(item['url']):
                raise ValueError('Untrusted IS article origin')
            self.rows.setdefault(item['url'], {'title':item['title'], 'status':'pending',
                'sequence':i, 'discovered_at':self.now.isoformat(), 'checked_at':None})
            self.rows[item['url']]['title'] = item['title']
        # The queue can survive a failed workflow whose partial reviews DB was
        # not published. Never let a cached success hide such an unsaved review.
        for url, row in self.rows.items():
            if url in imported:
                row['status'] = 'imported'
            elif row['status'] == 'imported':
                row['status'] = 'pending'
        self.save()

    def due(self, budget):
        due = []
        for url, row in self.rows.items():
            if row['status'] == 'imported':
                continue
            checked = datetime.fromisoformat(row['checked_at']) if row['checked_at'] else None
            expiry = timedelta(hours=12 if row['status'] == 'failed' else 168)
            if row['status'] == 'pending' or checked is None or checked <= self.now-expiry:
                due.append((url,row))
        # Pending backlog first; within retries/overlap oldest check first.
        due.sort(key=lambda item:(item[1]['status'] != 'pending',
            item[1]['checked_at'] or item[1]['discovered_at'],item[1]['sequence'],item[0]))
        return [{'url':url, 'title':row['title']} for url,row in due[:max(0,budget)]]

    def finish(self, url, status):
        self.rows[url]['status'] = status
        self.rows[url]['checked_at'] = self.now.isoformat()
        self.save()

    def queued(self):
        return sum(row['status'] in ('pending','failed') for row in self.rows.values())

    def failed(self):
        return sum(row['status'] == 'failed' for row in self.rows.values())

    def save(self):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=self.path.parent,prefix='.is-queue-')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as out:
                json.dump({'version':1,'articles':self.rows},out,ensure_ascii=False,indent=2)
                out.write('\n')
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
