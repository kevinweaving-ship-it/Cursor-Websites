#!/usr/bin/env python3
"""Read-only reuse of SailingSA's EXISTING public media/news APIs. No new credentials."""
import argparse,json,pathlib,requests,datetime as dt
ROOT=pathlib.Path(__file__).resolve().parent.parent
BASE='https://sailingsa.co.za'
def get(path):
 r=requests.get(BASE+path,timeout=30,headers={'User-Agent':'SailingSA-REA-Editorial/1.0'});r.raise_for_status();return r.json()
def run(issue,ids):
 out=ROOT/'issues'/issue/'sources'/'existing-sailingsa-media.json';out.parent.mkdir(parents=True,exist_ok=True)
 data={'provenance':'SailingSA public API','fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'news':get('/api/news/latest'),'sailors':{}}
 for i in ids:
  try:data['sailors'][str(i)]=get('/api/member/'+str(i)+'/public-mentions')
  except Exception as e:data['sailors'][str(i)]={'error':str(e)}
 out.write_text(json.dumps(data,indent=2,ensure_ascii=False))
 print(json.dumps({'path':str(out),'news_count':len(data['news']),'sailor_counts':{k:len(v.get('items',[])) for k,v in data['sailors'].items()}}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--issue',default='2026-09-28');p.add_argument('--sa-id',action='append',default=[]);a=p.parse_args();run(a.issue,a.sa_id)
