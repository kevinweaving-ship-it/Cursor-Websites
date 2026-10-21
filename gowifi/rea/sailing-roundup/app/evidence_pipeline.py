"""Verified event evidence shared by discovery, recap writing and publication."""
from __future__ import annotations
import concurrent.futures, datetime as dt, hashlib, json, re, urllib.parse, urllib.request
from bs4 import BeautifulSoup

MEDIA_EXCLUSIONS = {"https://rsa505.org.za/images/20261013_101619-COLLAGE.jpg":"Photographed results sheet is labelled 2025; not verified as 2026 event photography."}
TRACKING = {"fbclid","gclid","mc_cid","mc_eid"}
BAD_HOSTS = ("dart.dev","dartpad.dev","dart.org","dartcontainer.com","wikipedia.org","wikimedia.org")
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

TITLE_STOP={"the","and","for","with","from","that","this","2026","2025","2024","sailing","event","sa","sas","open","club","yacht","at","of","inc","incorporating","class"}
FOREIGN_EVENT_SLUG = re.compile(r"(dart-18-nationals|420-nationals|505-nationals|dabchick-gauteng|kzn-mirror-regionals|mac-tsl-wc-team-sailing)")
# Facebook / club URLs that belong to one event only. Bottle at the same club must not inherit Dart Nationals media.
EVENT_BOUND_SOURCES = (
    (re.compile(r"1pgpy1pgh1|1633819895206118|19vlskghbk|hmyc\.org\.za/events/367984", re.I), "dart-18-nationals"),
    (re.compile(r"420nationalssouthafrica|1jh51cdmew", re.I), "420-nationals"),
    (re.compile(r"id=338|505-nationals-2026|1mhjnwcfsm", re.I), "505-nationals"),
    (re.compile(r"dabchickca/events/358939", re.I), "dabchick-gauteng"),
)

def event_title_tokens(title):
    return [w for w in re.findall(r"[a-z0-9]+",(title or "").lower()) if w not in TITLE_STOP and len(w)>2]

def source_blob(item):
    return " ".join(str(item.get(k) or "") for k in ("url","source_url","title","headline","description","snippet","body","text")).lower()

def other_event_conflict(item,facts,require_identity=True):
    """Auto rule: a source about another event can never attach here.

    Why: Dam Bottle Sprints (mixed fleet at HMYC) accepted a Dart 18 Nationals
    Facebook post because verify treated class+venue+year, or host_club_page, as
    identity. Weekly generation and old-week rebuilds must reject that, not rely
    on a hand edit of the published HTML.

    require_identity=True is for incoming sources (must be about this event).
    False is for our own recap paragraphs (reject only a quote of another event).
    """
    slug=(facts.get("slug") or facts.get("event_id") or facts.get("id") or "").lower()
    title=facts.get("title") or facts.get("event_name") or ""
    blob=source_blob(item)
    url=canonical(item.get("url") or item.get("source_url"))
    official=canonical(facts.get("url") or facts.get("event_url") or "")
    if url and official and url==official:
        return None
    for match in re.finditer(r"/regatta/([a-z0-9\-]+)",blob):
        if slug and match.group(1)!=slug:
            return "different_event"
    for pat, need in EVENT_BOUND_SOURCES:
        if pat.search(blob) and need not in slug:
            return "other_event"
    foreign=FOREIGN_EVENT_SLUG.search(blob)
    if foreign and (not slug or foreign.group(1) not in slug):
        return "other_event"
    if re.search(r"\bnationals?\b",blob) and "national" not in title.lower():
        return "other_event"
    if re.search(r"\bregionals?\b",blob) and "regional" not in title.lower() and not any(t in blob for t in event_title_tokens(title)):
        return "other_event"
    if require_identity:
        distinctive=[t for t in event_title_tokens(title) if t not in {"dart"}]
        if distinctive and blob.strip() and not any(t in blob for t in distinctive):
            return "other_event"
    return None

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
    conflict=other_event_conflict(item,facts)
    if conflict:return {"accepted":False,"reason":conflict,"matches":[]}
    body=text_of(item);blob=(item.get("title","")+" "+body).lower()
    if len(body)<40:return {"accepted":False,"reason":"no_article_or_caption"}
    from search_everywhere import in_coverage_window
    window=in_coverage_window(item,facts)

    klass=str(facts.get("class_name") or "").lower()
    mixed=bool(facts.get("mixed_class"))
    class_match=bool(klass and re.search(r"(?<![a-z0-9])"+re.escape(klass)+r"(?![a-z0-9])",blob))
    title_hit=any(t in blob for t in event_title_tokens(facts.get("title") or ""))
    if mixed:
        class_match=class_match or title_hit
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
    matches=(["class"] if class_match else [])+(["venue"] if venue else [])+(["title"] if title_hit else [])+["person:"+n for n in names]
    # Class + venue + year is not identity. This event's title tokens or two of its sailors must appear.
    identity=title_hit or len(names)>=2
    accepted=identity and (class_match or title_hit) and (venue or title_hit) and (window is True or late_report or identity)
    return {"accepted":bool(accepted),"reason":("late_report_matched" if late_report else "event_identity_matched") if accepted else "insufficient_event_identity","matches":matches}

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
        # Youth identity must come from the official fleet and the source's title statement.
        if re.search(r"\bU-?17\b|under[- ]17",body,re.I):
            paragraphs=re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z])",body)
            for i,paragraph in enumerate(paragraphs):
                if not re.search(r"\bU-?17\b|under[- ]17",paragraph,re.I):continue
                nearby=" ".join(paragraphs[max(0,i-2):i+1])
                names=[n for n in facts.get("names",[]) if n in nearby]
                names=list(dict.fromkeys(names))
                if len(names)>=2 and re.search(r"1st|first|champion|won",paragraph,re.I):
                    key=tuple(names[:2])
                    if key not in seen:
                        notes.append(f"{' and '.join(names[:2])} also won the under-17 title, according to the published report. [{cite}]");seen.add(key)
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
    return notes[:3]

def recap(facts,cluster,index):
    from event_rewrite import _heats,_date_span
    mark="[1]";winner=facts["winner"];singular=" and " not in winner;subject="He" if singular else "They"
    verb="finished" if facts.get("status","").lower()=="provisional" else "won"
    title=facts["title"];venue=facts["club_name"];entries=facts.get("entries",0);races=facts.get("races",0)
    classes=[c for c in (facts.get("classes") or []) if c]
    klass=facts.get("winner_class") or facts.get("class_name") or ""
    if verb=="finished":
        opening=f"{winner} finished first in the published {title} standings at {venue}"
    else:opening=f"{winner} won the {title} at {venue}"
    if facts.get("mixed_class") and classes:
        opening+=f", taking the {klass or classes[0]} fleet on {facts['winner_nett']} nett points across {races} races. {entries} boats raced in {', '.join(classes)}. {mark}"
    else:
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
    if facts.get("mixed_class") and facts.get("ranked_rows"):
        by={}
        for row in facts["ranked_rows"]:
            key=(row.get("class_name") or row.get("class_canonical") or "").strip()
            if key:by.setdefault(key,[]).append(row)
        bits=[]
        for key,rs in by.items():
            names=[]
            for row in rs[:3]:
                n=(row.get("helm_name") or "").strip()
                if n:names.append(n)
            if names:bits.append(f"{key} 1–{len(names)} {', '.join(names)}")
        if bits:paragraphs.append("; ".join(bits)+f" {mark}")
    else:
        podium=[]
        if facts.get("second"):
            podium.append(f"{facts['second']} finished second on {facts['second_nett']} nett points.")
        if facts.get("third"):
            podium.append(f"{facts['third']} finished third on {facts['third_nett']} nett points.")
        if podium:paragraphs.append(" ".join(podium)+" "+mark)
    if facts.get("tied_first"):
        paragraphs.append(f"The top two crews were level on nett points; the official results rank {winner} first. {mark}")
    paragraphs.extend(source_notes(cluster,facts,index))
    if facts.get("status","").lower()=="provisional":
        paragraphs.append(f"The published results remain provisional. {mark}")
    return paragraphs

def feature(issue,monday,events,articles):
    from events_weekend import saturday_sunday
    sat,sun=saturday_sunday(monday)
    reports=[a for a in articles if a.get("type")=="regatta_report"]
    date_line=f"{sat.day}–{sun.strftime('%-d %B %Y')}"
    paragraphs=[]
    hero=None
    if not reports:
        paragraphs.append(f"No scored results were published for {date_line}.")
    elif len(reports)==1:
        from event_rewrite import is_chrome_image
        lead=reports[0]
        hero=lead.get("hero_image") or None
        if hero and is_chrome_image(hero.get("url") or "", hero.get("source_url") or hero.get("url") or ""):
            hero=None
        paragraphs.append(f"{lead.get('headline') or 'Weekend racing'}. {lead.get('deck') or ''}".strip())
    else:
        paragraphs.append(f"{len(reports)} scored events over {date_line}:")
        for report in reports:
            paragraphs.append(report.get("headline") or report.get("event_id") or "Weekend racing")
    covered={a.get("event_id") for a in reports}
    missing=sorted({e.get("event_name") for e in events if e.get("event_name") and (e.get("regatta_id") or "") not in covered and not e.get("has_results")})
    if missing:
        paragraphs.append("Also on the calendar, with no published results card: "+", ".join(missing)+".")
    blocks=[]
    if hero and hero.get("url") and len(reports)==1:
        blocks.append({"type":"image","url":hero.get("url"),"alt":reports[0].get("headline") or "Last Week's Roundup","caption":(reports[0].get("kicker") or "Weekend racing")+".","credit":"Event photography","source_url":hero.get("source_url") or "","rights_status":"source_attributed"})
    blocks+=[{"type":"paragraph","text":t} for t in paragraphs]
    return {"id":"sailing-"+issue,"type":"feature","headline":"Last Week's Roundup",
        "deck":date_line,"byline":"SailingSA","kicker":"SAILING","published_at":issue,
        "event_id":"sailing-"+issue,"layout":"lead","hero_image":hero,
        "blocks":blocks,"sources":["https://sailingsa.co.za/api/events"]+[f"https://sailingsa.co.za/regatta/{a['id']}" for a in reports if a.get("id")],
        "review_status":"rewritten"}


def photo_caption(image,facts,cluster):
    source=next((a for a in cluster.get("articles",[]) if canonical(a.get("url"))==canonical(image.get("source_url"))),{})
    body=text_of(source)
    names=[n for n in facts.get("names",[]) if n in body]
    names=list(dict.fromkeys(names))
    if re.search(r"\bU-?17\b|under[- ]17",body,re.I) and len(names)==2:
        return " and ".join(names)+" — under-17 champions."
    return facts["title"]+" — "+facts["club_name"]+"."
