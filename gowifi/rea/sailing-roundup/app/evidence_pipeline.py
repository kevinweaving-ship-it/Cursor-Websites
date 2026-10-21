"""Verified event evidence shared by discovery, recap writing and publication."""
from __future__ import annotations
import concurrent.futures, datetime as dt, hashlib, json, re, urllib.parse, urllib.request
from bs4 import BeautifulSoup

MEDIA_EXCLUSIONS = {"https://rsa505.org.za/images/20261013_101619-COLLAGE.jpg":"Photographed results sheet is labelled 2025; not verified as 2026 event photography."}
TRACKING = {"fbclid","gclid","mc_cid","mc_eid"}
BAD_HOSTS = ("dart.dev","dartpad.dev","dart.org","dartcontainer.com","wikipedia.org","wikimedia.org")
PLACE_CLAIM = re.compile(
    r"(?P<place>\d+)(?:st|nd|rd|th)\s*[–\-]\s*"
    r"(?P<name>[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)+)"
    r"(?:\s*\((?P<club>[A-Z0-9]{2,8})\))?"
)
AGE_LABEL = re.compile(r"\b(?:U-?(?P<u>\d{1,2})|under[- ](?P<under>\d{1,2}))\b", re.I)
WIN_CLAIM = re.compile(
    r"\b(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z'\-]+){1,2})"
    r"(?:[ \t]+and[ \t]+(?P<crew>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z'\-]+){1,2}))?"
    r"[ \t]+(?:won|wins|were crowned|was crowned|named)\b"
)
NAME_STOP = frozenset({
    "school","high","club","yacht","sports","national","nationals","championship",
    "sailing","results","overall","fleet","class","under","junior","youth","south",
    "africa","sailors","report","event","open","masters",
})
MAX_SOURCE_NOTES = 8
def canonical(url):
    p=urllib.parse.urlsplit((url or "").strip())
    host=p.netloc.lower().removeprefix("www.").replace("m.facebook.com","facebook.com")
    query=urllib.parse.urlencode([(k,v) for k,v in urllib.parse.parse_qsl(p.query) if not k.startswith("utm_") and k not in TRACKING])
    return urllib.parse.urlunsplit(("https",host,p.path.rstrip("/"),query,"")) if host else ""

def text_of(item):
    if item.get("body"): return item["body"].strip()
    out=[]
    for key in ("description","snippet"):
        text=(item.get(key) or "").strip()
        if text and not any(text in old for old in out):
            out=[old for old in out if old not in text]; out.append(text)
    return "\n".join(out) or (item.get("title") or "")

def _jsonld(soup):
    def walk(obj):
        if isinstance(obj,list):
            for x in obj: yield from walk(x)
        elif isinstance(obj,dict):
            yield obj
            for x in obj.get("@graph",[]): yield from walk(x)
    for s in soup.select('script[type="application/ld+json"]'):
        try: yield from walk(json.loads(s.string or s.get_text()))
        except (ValueError,TypeError): pass

def extract(url):
    headers={"User-Agent":"Mozilla/5.0 (compatible; SailingRoundupResearch/1.0)"}
    if "facebook.com" in url: headers["User-Agent"]="facebookexternalhit/1.1"
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=18) as r:
            raw=r.read(3_000_000).decode("utf-8","replace"); final=r.url
    except Exception as exc: return {"url":url,"fetch_status":"failed","error":type(exc).__name__}
    soup=BeautifulSoup(raw,"html.parser")
    def meta(key):
        t=soup.find("meta",attrs={"property":key}) or soup.find("meta",attrs={"name":key})
        return (t.get("content") or "").strip() if t else ""
    c=soup.find("link",rel="canonical")
    result={"url":urllib.parse.urljoin(final,c.get("href")) if c and c.get("href") else meta("og:url") or final,
        "title":meta("og:title") or (soup.title.get_text(" ",strip=True) if soup.title else ""),
        "description":meta("og:description") or meta("description"),"published":meta("article:published_time") or meta("pubdate"),
        "image":meta("og:image"),"fetched_at":dt.datetime.now(dt.timezone.utc).isoformat(),"fetch_status":"ok"}
    bodies=[]
    for ld in _jsonld(soup):
        if ld.get("articleBody"): bodies.append(str(ld["articleBody"]))
        if ld.get("datePublished") and not result["published"]:result["published"]=str(ld["datePublished"])
    if "facebook.com" in url:
        from facebook_cross_share import facebook_message_from_html
        caption=facebook_message_from_html(raw)
        if caption: bodies.append(caption)
        if not result["published"]:
            m=re.search(r'"(?:creation_time|publish_time)":(\d{10})',raw)
            if m: result["published"]=dt.datetime.fromtimestamp(int(m[1]),dt.timezone.utc).isoformat()
    else:
        article=soup.select_one("[itemprop=articleBody],.com-content-article__body,article .entry-content,article .td-post-content,article,main .entry-content,.entry-content")
        if article:
            for x in article.select("script,style,nav,footer,aside,form"):x.decompose()
            paragraphs=[]
            for p in article.select("p,li"):
                text=re.sub(r"\s+"," ",p.get_text(" ",strip=True))
                if len(text)>30 and text not in paragraphs:paragraphs.append(text)
            if paragraphs:bodies.append("\n".join(paragraphs))
        if not result["published"]:
            time=soup.find("time")
            if time:result["published"]=time.get("datetime") or ""
    images=[]
    for image in soup.select("figure.item-image img,.com-content-article__images img,article img,[itemprop=articleBody] img"):
        src=image.get("data-src") or image.get("src") or ""
        if src:
            images.append({"url":urllib.parse.urljoin(final,src),"source_url":result["url"],"title":image.get("alt") or result["title"]})
    result["images"]=images
    if images:result["image"]=images[0]["url"]
    result["body"]=max(bodies,key=len)[:30000] if bodies else result["description"]
    result["snippet"]=result["body"][:700]
    result["canonical_url"]=canonical(result["url"])
    return result

def _norm_name(name):
    return re.sub(r"[^a-z0-9]+"," ",(name or "").lower()).strip()

def official_names(facts):
    names=[]
    for n in facts.get("names") or []:
        if n and str(n).strip(): names.append(str(n).strip())
    for fleet in facts.get("fleets") or []:
        for n in fleet.get("names") or []:
            if n and str(n).strip(): names.append(str(n).strip())
        for row in fleet.get("ranked_rows") or []:
            for key in ("helm_name","crew_name"):
                if row.get(key): names.append(str(row[key]).strip())
    for row in facts.get("ranked_rows") or []:
        for key in ("helm_name","crew_name"):
            if row.get(key): names.append(str(row[key]).strip())
    return list(dict.fromkeys(n for n in names if n))

def match_official_name(claimed,official):
    claimed=_norm_name(claimed)
    if not claimed or len(claimed.split())<2: return None
    if any(part in NAME_STOP for part in claimed.split()): return None
    for name in official:
        other=_norm_name(name)
        if not other: continue
        if claimed==other or claimed.startswith(other) or other.startswith(claimed):
            return name
        if set(claimed.split())<=set(other.split()) or set(other.split())<=set(claimed.split()):
            return name
    return None

def age_phrase(match):
    if not match: return ""
    raw=match.groupdict().get("u") or match.groupdict().get("under") or ""
    try: return f"under-{int(raw)}"
    except (TypeError,ValueError): return ""

def _age_near(text,start,end,window=48):
    return AGE_LABEL.search((text or "")[max(0,start-window):end+window])

def official_place(facts,name):
    target=_norm_name(name)
    if not target: return None
    for row in facts.get("ranked_rows") or []:
        people=[_norm_name(row.get("helm_name") or ""),_norm_name(row.get("crew_name") or "")]
        if target in people or any(target==p or (p and (target.startswith(p) or p.startswith(target))) for p in people if p):
            rank=row.get("rank")
            return int(rank) if str(rank).isdigit() else None
    return None

def results_checksum(item,facts):
    """External media must name this event's official sailors.

    Claimed overall leaders (1st/2nd/3rd, won, champion) have to appear in
    SailingSA results. A different event's winner is a checksum miss. Age
    titles are not overall leader claims. Extra host-club names only fail
    the source when the official fleet snapshot is complete.
    """
    official=official_names(facts)
    digest=hashlib.sha256("|".join(sorted(_norm_name(n) for n in official)).encode()).hexdigest()[:12] if official else ""
    body=text_of(item)
    blob=(item.get("title") or "")+"\n"+body
    if not official:
        return {"ok":True,"reason":"no_official_names","official_digest":digest,"claimed_leaders":[],"unknown_leaders":[]}
    claimed=[];unknown=[]
    for match in PLACE_CLAIM.finditer(blob):
        name=match.group("name").strip()
        place=int(match.group("place"))
        if len(_norm_name(name).split())<2: continue
        age=age_phrase(_age_near(blob,match.start(),match.end()))
        claimed.append({"name":name,"place":place,"age":age})
        if age or place>3: continue
        if not match_official_name(name,official):
            unknown.append({"name":name,"place":place,"reason":"unknown_leader"})
        else:
            got=official_place(facts,match_official_name(name,official))
            if got is not None and got!=place:
                unknown.append({"name":name,"place":place,"official_place":got,"reason":"leader_mismatch"})
    for match in WIN_CLAIM.finditer(blob):
        if _age_near(blob,match.start(),match.end()): continue
        for key in ("name","crew"):
            name=(match.group(key) or "").strip()
            if not name or any(part in NAME_STOP for part in _norm_name(name).split()): continue
            claimed.append({"name":name,"place":1,"age":""})
            if not match_official_name(name,official):
                unknown.append({"name":name,"place":1,"reason":"unknown_leader"})
            else:
                got=official_place(facts,match_official_name(name,official))
                if got is not None and got!=1:
                    unknown.append({"name":name,"place":1,"official_place":got,"reason":"leader_mismatch"})
    rows=facts.get("ranked_rows") or []
    complete=bool(facts.get("entries")) and len(rows)>=int(facts.get("entries") or 0) and int(facts.get("entries") or 0)>0
    if complete:
        for match in PLACE_CLAIM.finditer(blob):
            name=match.group("name").strip()
            if match_official_name(name,official): continue
            if any(part in NAME_STOP for part in _norm_name(name).split()): continue
            if len(_norm_name(name).split())<2: continue
            unknown.append({"name":name,"place":int(match.group("place")),"reason":"unknown_sailor"})
    if unknown:
        reason="leader_mismatch" if any(x.get("reason")=="leader_mismatch" for x in unknown) else "unknown_leader"
        return {"ok":False,"reason":reason,"official_digest":digest,"claimed_leaders":claimed,"unknown_leaders":unknown}
    return {"ok":True,"reason":"matched" if claimed else "no_leader_claim","official_digest":digest,"claimed_leaders":claimed,"unknown_leaders":[]}

def verify(item,facts):
    url=canonical(item.get("url") or item.get("source_url"))
    if url==canonical(facts.get("url")):return {"accepted":True,"reason":"official_results","matches":["canonical_event_id"]}
    p=urllib.parse.urlsplit(url);path=p.path.lower()
    if not p.netloc or any(p.netloc==h or p.netloc.endswith("."+h) for h in BAD_HOSTS):
        return {"accepted":False,"reason":"unrelated_host"}
    if "sailingsa.co.za"==p.netloc and path.startswith("/regatta/"):
        return {"accepted":False,"reason":"different_event"}
    if any(x in path for x in ("/login","/accounts/","/share/g/")) or path in ("","/home","/gallery","/photos"):
        return {"accepted":False,"reason":"directory_or_login"}
    if p.netloc=="facebook.com" and not any(x in path for x in ("/posts/","/permalink/","/share/p/","/videos/","/reel/")) and not p.query:
        return {"accepted":False,"reason":"social_directory"}
    body=text_of(item);blob=(item.get("title","")+" "+body).lower()
    if len(body)<40:return {"accepted":False,"reason":"no_article_or_caption"}
    from search_everywhere import in_coverage_window
    window=in_coverage_window(item,facts)

    classes=[str(x).lower() for x in ([facts.get("class_name")] + list(facts.get("class_names") or [])) if x]
    class_match=any(klass and re.search(r"(?<![a-z0-9])"+re.escape(klass)+r"(?![a-z0-9])",blob) for klass in dict.fromkeys(classes))
    aliases=[facts.get("club_name",""),facts.get("club","")]
    aliases += [re.sub(r"\b(yacht|sports|club)\b","",facts.get("club_name",""),flags=re.I).strip()]
    venue=any(len(a.strip())>=3 and re.search(r"(?<![a-z0-9])"+re.escape(a.strip().lower())+r"(?![a-z0-9])",blob) for a in aliases)
    names=list(dict.fromkeys(n for n in facts.get("names",[]) if len(n.split())>=2 and n.lower() in blob))
    years=set(re.findall(r"\b20\d{2}\b",blob)); year=str(facts.get("start",""))[:4]
    if years and year not in years:return {"accepted":False,"reason":"wrong_year"}
    late_report=False
    if window is False:
        try:
            published=dt.date.fromisoformat(str(item.get("published") or item.get("published_at") or "")[:10])
            end=dt.date.fromisoformat(str(facts["end"])[:10])
            late_report=(end<published<=end+dt.timedelta(days=28) and class_match and venue and len(names)>=2 and year in (item.get("title") or ""))
        except (ValueError,KeyError):pass
        if not late_report:return {"accepted":False,"reason":"outside_event_window"}
    matches=(["class"] if class_match else [])+(["venue"] if venue else [])+["person:"+n for n in names]
    # A label such as seed/host/verified is never an identity proof.
    accepted=class_match and (venue or len(names)>=2) and (window is True or late_report or (venue and len(names)>=2) or (year in years and venue))
    checksum=results_checksum(item,facts)
    if accepted and not checksum["ok"]:
        return {"accepted":False,"reason":"results_checksum_failed","matches":matches,"checksum":checksum}
    return {"accepted":bool(accepted),"reason":("late_report_matched" if late_report else "event_identity_matched") if accepted else "insufficient_event_identity","matches":matches,"checksum":checksum}

def verified_cluster(facts,candidates,fetch=True):
    candidates=list(candidates)
    if fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            fetched=list(pool.map(extract,[x.get("url") or x.get("source_url") or "" for x in candidates]))
        merged=[]
        for original,doc in zip(candidates,fetched):
            item=dict(original)
            if doc.get("fetch_status")=="ok":
                cached_body=text_of(original)
                item.update({k:v for k,v in doc.items() if v})
                if "facebook.com" in item.get("url","") and len(cached_body)>len(item.get("body","")):
                    item["body"]=cached_body
                    item["body_provenance"]="previously_retrieved_caption"
            else:item["fetch_status"]=doc.get("fetch_status")
            merged.append(item)
        candidates=merged
    kept=[];rejected=[];seen_urls=set();seen_text=set()
    for item in candidates:
        item=dict(item);item["verification"]=verify(item,facts)
        if not item["verification"]["accepted"]:
            rejected.append(item);continue
        key=canonical(item.get("url"));text=re.sub(r"\W+","",text_of(item).lower())
        digest=hashlib.sha256(text.encode()).hexdigest()
        post=re.search(r"/(?:posts|videos)/(?:[^/]+/)?(\d{8,})(?:/|$)",key)
        identity="facebook:"+post.group(1) if post else key
        if identity in seen_urls or (len(text)>=40 and digest in seen_text):
            item["verification"]={"accepted":False,"reason":"duplicate_source"};rejected.append(item);continue
        seen_urls.add(identity);seen_text.add(digest)
        item["source_id"]=hashlib.sha256(key.encode()).hexdigest()[:16]
        item["content_hash"]=digest;item["canonical_url"]=key;kept.append(item)
    return {"event_id":facts.get("slug"),"event_url":facts.get("url"),"articles":kept,"rejected":rejected,
        "count":len(kept),"reporting_count":sum(x["verification"]["reason"]!="official_results" for x in kept),
        "schema_version":"verified-evidence-1","media_review":[{"url":x.get("image"),"status":"rejected","reason":MEDIA_EXCLUSIONS[canonical(x["image"])]} for x in kept if canonical(x.get("image")) in MEDIA_EXCLUSIONS]}

def source_notes(cluster,facts,index):
    """Extract only supported, named facts. No guessed proper nouns or implied tie-break rules."""
    notes=[];seen=set()
    for item in cluster.get("articles",[]):
        body=text_of(item)
        if not verify(item,facts)["accepted"]:continue
        cite=next((x["n"] for x in index if canonical(x["url"])==canonical(item.get("url"))),None)
        if not cite:continue
        # Age titles only when verified media names official-result sailors.
        if AGE_LABEL.search(body):
            paragraphs=re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])",body)
            for i,paragraph in enumerate(paragraphs):
                age=AGE_LABEL.search(paragraph)
                if not age:continue
                label=age_phrase(age)
                if not label:continue
                nearby=" ".join(paragraphs[max(0,i-2):i+1])
                names=[n for n in official_names(facts) if n in nearby]
                names=list(dict.fromkeys(names))
                if names and re.search(r"1st|first|champion|won|title|winner",paragraph,re.I):
                    shown=names[:2]
                    key=("age",label)+tuple(shown)
                    if key not in seen:
                        notes.append(f"{' and '.join(shown)} also won the {label} title, according to the published report. [{cite}]");seen.add(key)
        if facts.get("tied_first") and re.search(r"won the tie break by winning the last race",body,re.I):
            notes.append(f"The class report attributes the title tie-break to {facts['winner']} winning the final race. [{cite}]")
        # Host club placing mentions are checked against the official rank and sailor name.
        rows=facts.get("ranked_rows",[])
        home=[]
        for row in rows:
            name=row.get("helm_name") or ""
            rank=str(row.get("rank") or "")
            if name and name in body and rank.isdigit() and int(rank)>3:
                if re.search(re.escape(name)+r"[^\n.!?]{0,70}\b"+rank+r"(?:th|st|nd|rd)?\b",body,re.I) or re.search(r"\b"+rank+r"(?:th|st|nd|rd)\s*[–-]\s*"+re.escape(name),body,re.I):
                    if str(row.get("club_abbrev") or row.get("club_raw") or "").upper()==str(facts.get("club","")).upper():
                        home.append(f"{name} ({rank}{'th' if int(rank)%100 in (11,12,13) else {1:'st',2:'nd',3:'rd'}.get(int(rank)%10,'th')})")
        if home:
            sentence=f"The host club's report also highlighted {', '.join(dict.fromkeys(home))}. [{cite}]"
            if sentence not in notes:notes.append(sentence)
    return notes[:MAX_SOURCE_NOTES]

def recap(facts,cluster,index):
    from event_rewrite import _heats,_date_span
    mark="[1]";winner=facts["winner"];singular=" and " not in winner;subject="He" if singular else "They"
    verb="finished" if facts.get("status","").lower()=="provisional" else "won"
    title=facts["title"];venue=facts["club_name"];entries=facts.get("entries",0);races=facts.get("races",0)
    if verb=="finished":
        opening=f"{winner} finished first in the published {title} standings at {venue}"
    else:opening=f"{winner} won the {title} at {venue}"
    opening+=f", scoring {facts['winner_nett']} nett points across {races} races in a {entries}-boat fleet. {mark}"
    paragraphs=[opening]
    heats=_heats(facts.get("winner_scores"))
    wins=sum(h.get("win",False) for h in heats)
    if heats and len(heats)==races:
        if wins==races:paragraphs.append(f"{winner} won every race in the series, held on {_date_span(facts['start'],facts['end'])}. {mark}")
        elif wins:paragraphs.append(f"{winner} recorded {wins} race {'win' if wins==1 else 'wins'} during the series, held on {_date_span(facts['start'],facts['end'])}. {mark}")
        else:paragraphs.append(f"{winner} topped the overall standings without winning an individual race. {mark}")
        late=heats[-4:];late_wins=sum(h.get("win",False) for h in late)
        if wins!=races and len(late)==4 and late_wins>=3:
            ending=" and won the final race" if late_wins < 4 and heats[-1].get("win") else ""
            paragraphs.append(f"{winner} won {late_wins} of the final four races{ending}. {mark}")
    podium=[]
    if facts.get("second"):
        podium.append(f"{facts['second']} finished second on {facts['second_nett']} nett points.")
    if facts.get("third"):
        podium.append(f"{facts['third']} finished third on {facts['third_nett']} nett points.")
    if podium:paragraphs.append(" ".join(podium)+" "+mark)
    if facts.get("multi_class"):
        extras=[]
        for fleet in facts.get("fleets") or []:
            if not fleet.get("winner") or not fleet.get("class_name"): continue
            if fleet.get("class_name")==facts.get("class_name") and fleet.get("winner")==winner: continue
            extras.append(f"{fleet['winner']} won the {fleet['class_name']} on {fleet.get('winner_nett') or 'the published'} nett points in a {fleet.get('entries') or 0}-boat fleet.")
        if extras:paragraphs.append(" ".join(extras)+" "+mark)
    if facts.get("tied_first"):
        paragraphs.append(f"The top two crews were level on nett points; the official results rank {winner} first. {mark}")
    paragraphs.extend(source_notes(cluster,facts,index))
    if facts.get("status","").lower()=="provisional":
        paragraphs.append(f"The published results remain provisional. {mark}")
    return paragraphs

def feature(issue,monday,events,articles):
    from events_weekend import previous_week, saturday_sunday
    week_start, week_end = previous_week(monday)
    sat, sun = saturday_sunday(monday)
    reports=[a for a in articles if a.get("type")=="regatta_report"]
    span = f"{week_start.day}–{week_end.strftime('%-d %B %Y')}"
    lead = "Four fleets raced at Aeolians, Henley Midmar and Theewater over the weekend." if len(reports)==4 and issue=="2026-09-28" else f"{len(reports)} scored events feature in the sailing roundup for {span}."
    paragraphs=[lead]
    covered={a.get("event_id") for a in reports}
    missing=sorted({e.get("event_name") for e in events if e.get("event_name") and e.get("regatta_id") not in covered})
    if missing:
        paragraphs.append("The calendar also listed "+", ".join(missing)+". Results for those events were not available in the source snapshot.")
    return {"id":"sailing-"+issue,"type":"feature","headline":"South African Sailing — The Weekend Roundup",
        "deck": f"{sat.day}–{sun.strftime('%-d %B %Y')}" if issue=="2026-09-28" else span, "byline":"SailingSA","kicker":"SAILING","published_at":issue,
        "event_id":"sailing-"+issue,"layout":"lead","hero_image":None,"blocks":[{"type":"paragraph","text":t} for t in paragraphs],
        "sources":["https://sailingsa.co.za/api/events"],"review_status":"rewritten"}


def photo_caption(image,facts,cluster):
    source=next((a for a in cluster.get("articles",[]) if canonical(a.get("url"))==canonical(image.get("source_url"))),{})
    body=text_of(source)
    names=[n for n in official_names(facts) if n in body]
    names=list(dict.fromkeys(names))
    age=AGE_LABEL.search(body)
    label=age_phrase(age)
    if label and names:
        return " and ".join(names[:2])+f" — {label} champions."
    return facts["title"]+" — "+facts["club_name"]+"."
