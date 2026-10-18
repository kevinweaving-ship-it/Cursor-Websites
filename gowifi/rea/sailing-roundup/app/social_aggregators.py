#!/usr/bin/env python3
"""REA social ingestion: Athena (Apify) and SocialCrawl. Independent of SailingSA production."""
import argparse,datetime as dt,json,os,pathlib,sqlite3,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent.parent
DB=ROOT/'data'/'sources.sqlite3'
def request(url,payload=None,headers=None,timeout=75):
 h={'User-Agent':'SailingSA-REA-Roundup/1.0','Accept':'application/json'}
 h.update(headers or {})
 body=None if payload is None else json.dumps(payload).encode()
 if body:h['Content-Type']='application/json'
 req=urllib.request.Request(url,data=body,headers=h)
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read())
def athena(urls):
 key=os.getenv('APIFY_TOKEN')
 if not key:return {'status':'needs_credentials','provider':'athena','env':'APIFY_TOKEN'}
 actor='ranil~athena-social-scraper'
 data=request('https://api.apify.com/v2/acts/'+actor+'/run-sync-get-dataset-items?token='+urllib.parse.quote(key),{'startUrls':[{'url':u} for u in urls],'useBrowserFallback':True},timeout=240)
 return {'status':'ok','provider':'athena','items':data}
def socialcrawl(query,platform='search',resource='everywhere'):
 key=os.getenv('SOCIALCRAWL_API_KEY')
 if not key:return {'status':'needs_credentials','provider':'socialcrawl','env':'SOCIALCRAWL_API_KEY'}
 base=os.getenv('SOCIALCRAWL_BASE_URL','https://www.socialcrawl.dev').rstrip('/')
 params={'query':query}
 url=base+'/v1/'+urllib.parse.quote(platform)+'/'+resource+'?'+urllib.parse.urlencode(params)
 data=request(url,headers={'x-api-key':key})
 return {'status':'ok','provider':'socialcrawl','items':data}
def known_sources():
 with sqlite3.connect(DB) as c:
  return [{'entity_type':r[0],'entity_key':r[1],'platform':r[2],'url':r[3]} for r in c.execute("SELECT entity_type,entity_key,platform,url FROM sources WHERE platform IN ('facebook','instagram','tiktok','youtube') AND confidence IN ('confirmed_directory','confirmed_official')")]
def save(provider,items,issue):
 out=ROOT/'issues'/issue/'sources'/(provider+'-aggregator.json')
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'provider':provider,'fetched_at':dt.datetime.now(dt.timezone.utc).isoformat(),'items':items},indent=2,ensure_ascii=False))
 return str(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--provider',choices=['athena','socialcrawl','both'],default='both');p.add_argument('--issue',default='2026-09-28');p.add_argument('--query',default='2026 420 Nationals Theewater Sports Club September 2026 sailing');p.add_argument('--urls',nargs='*');a=p.parse_args()
 results=[]
 if a.provider in ('athena','both'):
  urls=a.urls or [s['url'] for s in known_sources()]
  if urls:
   try:r=athena(urls)
   except Exception as e:r={'provider':'athena','status':'error','error':str(e)}
   if r['status']=='ok':r['saved']=save('athena',r['items'],a.issue);r['count']=len(r['items']) if isinstance(r['items'],list) else None;r.pop('items',None)
   results.append(r)
 if a.provider in ('socialcrawl','both'):
  try:r=socialcrawl(a.query)
  except Exception as e:r={'provider':'socialcrawl','status':'error','error':str(e)}
  if r['status']=='ok':r['saved']=save('socialcrawl',r['items'],a.issue);r.pop('items',None)
  results.append(r)
 print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':main()
