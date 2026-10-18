#!/usr/bin/env python3
"""Persistent independent source registry. Never writes to SailingSA."""
import argparse,datetime as dt,json,pathlib,sqlite3
ROOT=pathlib.Path(__file__).resolve().parent.parent
DB=ROOT/'data'/'sources.sqlite3'
def connect():
 DB.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(DB)
 c.execute('PRAGMA foreign_keys=ON')
 c.executescript("""
 CREATE TABLE IF NOT EXISTS entities (
  entity_type TEXT NOT NULL, entity_key TEXT NOT NULL, display_name TEXT,
  sailingsa_url TEXT, last_seen TEXT, PRIMARY KEY(entity_type,entity_key));
 CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL,entity_key TEXT NOT NULL,
  platform TEXT NOT NULL,url TEXT NOT NULL, canonical_url TEXT NOT NULL,
  discovery_url TEXT NOT NULL, confidence TEXT NOT NULL DEFAULT 'candidate',
  review_note TEXT,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,
  UNIQUE(entity_type,entity_key,canonical_url),
  FOREIGN KEY(entity_type,entity_key) REFERENCES entities(entity_type,entity_key));
 CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY,source_id INTEGER NOT NULL,observed_at TEXT NOT NULL,
  evidence_url TEXT NOT NULL,evidence_title TEXT, event_key TEXT,
  event_date TEXT, media_url TEXT, media_type TEXT,
  verification TEXT NOT NULL DEFAULT 'unverified',
  FOREIGN KEY(source_id) REFERENCES sources(id));
 CREATE INDEX IF NOT EXISTS idx_observations_event ON observations(event_key,event_date);
 """)
 return c
def normalize(url):
 from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
 x=urlsplit(url)
 return urlunsplit((x.scheme.lower(),x.netloc.lower().removeprefix('www.'),x.path.rstrip('/') or '/',urlencode([(k,v) for k,v in parse_qsl(x.query) if k not in ('fbclid','mibextid','utm_source','utm_medium','utm_campaign')]),''))
def ingest(directory):
 data=json.loads(pathlib.Path(directory).read_text())
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 with connect() as c:
  for e in data:
   if not e.get('record','').startswith('https://sailingsa.co.za/'):continue
   parts=e['record'].split('/')
   if len(parts)<5:continue
   kind,key=parts[3],parts[4]
   c.execute('INSERT INTO entities VALUES(?,?,?,?,?) ON CONFLICT(entity_type,entity_key) DO UPDATE SET display_name=excluded.display_name,sailingsa_url=excluded.sailingsa_url,last_seen=excluded.last_seen',(kind,key,e.get('title'),e['record'],now))
   for s in e.get('links',[]):
    if s['platform']=='website' and '/events/' in s['url']:continue
    canonical=normalize(s['url'])
    c.execute("""INSERT INTO sources(entity_type,entity_key,platform,url,canonical_url,discovery_url,confidence,first_seen,last_seen)
     VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(entity_type,entity_key,canonical_url)
     DO UPDATE SET last_seen=excluded.last_seen""",(kind,key,s['platform'],s['url'],canonical,s['provenance'],'confirmed_directory',now,now))
 with connect() as c:
  return {'entities':c.execute('SELECT COUNT(*) FROM entities').fetchone()[0],
   'sources':c.execute('SELECT COUNT(*) FROM sources').fetchone()[0],
   'database':str(DB)}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--ingest',required=True);args=a.parse_args()
 print(json.dumps(ingest(args.ingest)))
