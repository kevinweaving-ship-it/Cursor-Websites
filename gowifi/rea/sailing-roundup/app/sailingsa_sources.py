#!/usr/bin/env python3
"""Extract authoritative external links from SailingSA's public club/class records."""
import argparse,json,pathlib,requests,urllib.parse
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parent.parent
PLATFORMS={'facebook.com':'facebook','instagram.com':'instagram','youtube.com':'youtube','youtu.be':'youtube','tiktok.com':'tiktok','x.com':'x','twitter.com':'x'}
def extract(kind,slug):
 url='https://sailingsa.co.za/'+kind+'/'+slug
 r=requests.get(url,timeout=22,headers={'User-Agent':'Mozilla/5.0'});r.raise_for_status()
 s=BeautifulSoup(r.text,'html.parser')
 links=[];seen=set()
 for a in s.select('a[href]'):
  href=urllib.parse.urljoin(r.url,a['href'])
  parsed=urllib.parse.urlparse(href)
  if parsed.scheme not in ('http','https') or href in seen:continue
  seen.add(href);host=parsed.netloc.lower().removeprefix('www.')
  platform=next((v for k,v in PLATFORMS.items() if host==k or host.endswith('.'+k)),None)
  if platform:links.append({'platform':platform,'url':href,'provenance':url})
  elif host and host not in ('sailingsa.co.za','www.sailingsa.co.za') and not any(x in host for x in ('google.com','g.page','schema.org','cloudflare','openstreetmap','facebook.net')):
   links.append({'platform':'website','url':href,'provenance':url})
 return {'record':url,'title':s.title.get_text(' ',strip=True) if s.title else '', 'links':links}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--club',action='append',default=[]);ap.add_argument('--class',dest='classes',action='append',default=[]);ap.add_argument('--issue',default='2026-09-28');a=ap.parse_args()
 result=[]
 for kind,slugs in [('club',a.club),('class',a.classes)]:
  for slug in slugs:
   try:result.append(extract(kind,slug))
   except Exception as e:result.append({'record':kind+'/'+slug,'error':str(e)[:180]})
 path=ROOT/'issues'/a.issue/'sources'/'sailingsa-social-directory.json'
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print(json.dumps({'records':len(result),'links':sum(len(x.get('links',[])) for x in result),'path':str(path),'data':result},ensure_ascii=False))
