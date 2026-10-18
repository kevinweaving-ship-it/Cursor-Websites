#!/usr/bin/env python3
"""Crawl verified club websites and linked public gallery sources. Evidence only; no unlicensed reuse."""
import argparse,collections,json,pathlib,re,requests,urllib.parse
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parent.parent
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; SailingRoundupResearch/0.1)'}
def crawl(club,maxpages=25):
 cfg=json.loads((ROOT/'app/club_sources.json').read_text())['clubs'][club]
 home=cfg['website'];domain=urllib.parse.urlparse(home).netloc
 queue=collections.deque([home]+[v for k,v in cfg.items() if k=='gallery'])
 visited=set();pages=[];media=[];external=[]
 while queue and len(visited)<maxpages:
  url=queue.popleft()
  if url in visited:continue
  visited.add(url)
  try:
   r=requests.get(url,headers=HEADERS,timeout=16)
   if r.status_code!=200 or 'html' not in r.headers.get('content-type',''):continue
   s=BeautifulSoup(r.text,'html.parser')
   title=s.title.get_text(' ',strip=True) if s.title else ''
   text=s.get_text(' ',strip=True)
   pages.append({'url':r.url,'title':title,'event_relevance':bool(re.search(r'2026|nationals|dart|420|gallery|photo|regatta',title+' '+text[:1000],re.I))})
   for a in s.select('a[href]'):
    link=urllib.parse.urljoin(r.url,a['href'])
    label=a.get_text(' ',strip=True)
    if urllib.parse.urlparse(link).netloc==domain and link not in visited and re.search(r'2026|2025|2024|gallery|news|event|sail|dart|420|national|photo',link+' '+label,re.I):
     queue.append(link)
    elif any(x in link for x in ('facebook.com','instagram.com','youtube.com')):
     if link not in external:external.append(link)
   for im in s.select('meta[property="og:image"],main img,article img,figure img'):
    src=im.get('content') or im.get('src') or im.get('data-src')
    if not src:continue
    link=urllib.parse.urljoin(r.url,src)
    if not any(x['image_url']==link for x in media):
     media.append({'image_url':link,'source_page':r.url,'page_title':title,'alt':im.get('alt',''),'rights_status':'review_required'})
  except Exception as e:pages.append({'url':url,'error':str(e)[:130]})
 return {'club':club,'pages':pages,'image_candidates':media,'social_links':external,'verified_event_images':0}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--club',required=True);a.add_argument('--issue',default='2026-09-28');a.add_argument('--maxpages',type=int,default=25);args=a.parse_args()
 result=crawl(args.club,args.maxpages)
 out=ROOT/'issues'/args.issue/'sources'/(args.club+'-club-crawl.json')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print(json.dumps({'club':args.club,'pages':len(result['pages']),'images':len(result['image_candidates']),'social_links':len(result['social_links']),'path':str(out)}))
