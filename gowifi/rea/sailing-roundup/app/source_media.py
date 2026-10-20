#!/usr/bin/env python3
"""Source-first media discovery: extract public image candidates with provenance, no republishing."""
import argparse,json,pathlib,requests,urllib.parse
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parent.parent
def inspect(url):
 r=requests.get(url,timeout=22,headers={'User-Agent':'Mozilla/5.0'});r.raise_for_status()
 s=BeautifulSoup(r.text,'html.parser')
 title=s.title.get_text(' ',strip=True) if s.title else ''
 items=[]
 for tag in s.select('meta[property="og:image"],meta[name="twitter:image"],article img,main img'):
  raw=tag.get('content') or tag.get('src') or tag.get('data-src')
  if not raw:continue
  link=urllib.parse.urljoin(r.url,raw)
  if link not in {x['image_url'] for x in items}:
   items.append({'image_url':link,'alt':tag.get('alt',''),'source_url':r.url,'source_title':title,'rights_status':'unknown','verification':'candidate_only'})
 return {'url':r.url,'title':title,'images':items[:30]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--issue',required=True);ap.add_argument('--event',required=True);ap.add_argument('--url',action='append',required=True);a=ap.parse_args()
 output={'event':a.event,'sources':[]}
 for url in a.url:
  try:output['sources'].append(inspect(url))
  except Exception as e:output['sources'].append({'url':url,'error':str(e)[:200]})
 path=ROOT/'issues'/a.issue/'sources'/(a.event+'-source-images.json')
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print(json.dumps({'path':str(path),'images':sum(len(x.get('images',[])) for x in output['sources']),'sources':len(output['sources'])}))
if __name__=='__main__':main()
