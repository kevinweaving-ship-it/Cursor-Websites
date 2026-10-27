"""Content-addressed editorial media rules shared by generation and rendering."""
from __future__ import annotations
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parent.parent
BANNED=re.compile(r"results?\s*(?:sheet|table)|score\s*sheet|scoresheet|standings\s*(?:sheet|table)",re.I)
def archive_context(facts,archive_year,caption):
    year=str(facts.get("end") or facts.get("start") or "")[:4]
    try:offset=int(year)-int(archive_year)
    except (ValueError,TypeError):raise ValueError("Invalid archive photograph year/label")
    if not 1 <= offset <= 3 or "archive" not in str(caption).lower() or str(archive_year) not in str(caption):
        raise ValueError("Invalid archive photograph year/label")
    result=dict(facts)
    mapping={}
    for key in ["start","end"]:
        value=str(facts.get(key) or "")
        if value[:4].isdigit():
            mapping[value[:4]]=str(int(value[:4])-offset)
            result[key]=mapping[value[:4]]+value[4:]
    for key in ["title","name"]:
        result[key]=re.sub(r"20\d{2}",lambda m:mapping.get(m[0],m[0]),str(facts.get(key) or ""))
    return result

def quick_archive(issue,root=None,event_end=None):
    p=(root or ROOT)/"data/media-publication-policy.json"
    policy=json.loads(p.read_text()).get("quick_archive",{}) if p.exists() else {}
    if not policy.get("allow_compact_without_deep_search"):return False
    day=str(event_end or issue)[:10]
    if event_end:
        import datetime as dt
        try:
            end=dt.date.fromisoformat(day)
            if str(end+dt.timedelta(days=7-end.weekday()))!=str(issue):return False
        except ValueError:return False
    return str(policy.get("from"))<=day<=str(policy.get("through"))

def valid_media_exception(exception):
    if not exception.get("evidence"):return False
    if exception.get("reason")=="no_verified_event_photo":
        return bool(exception.get("current_attempted") and exception.get("archive_attempted"))
    return bool(exception.get("reason")=="quick_archive_no_easy_verified_photo" and exception.get("quick_attempted") and exception.get("deep_search_waived_by_user"))

def rules(root=None):
    path=(root or ROOT)/"data"/"media-editorial.json"
    return json.loads(path.read_text()) if path.exists() else {"images":{},"supplements":{}}
def image_evidence(item,slug,root=None,issue=None):
    root=root or ROOT
    digest=item.get("content_hash")
    path=item.get("local_file") or item.get("local_path") or item.get("url") or ""
    if not digest and path and not path.startswith("http"):
        f=pathlib.Path(path)
        if not f.is_absolute() and issue:f=root/"issues"/issue/f
        if f.is_file():digest=hashlib.sha256(f.read_bytes()).hexdigest()
    known=rules(root).get("images",{}).get(digest or "")
    if known and known.get("event_id")==slug:return dict(known,verification=known.get("verification") or "reviewed_source_and_pixels")
    vision=item.get("vision") or {}
    category=vision.get("category") or item.get("category") or ""
    relevance=vision.get("relevance") or 0
    try:relevance=float(relevance)
    except (TypeError,ValueError):relevance=0
    # A source match alone does not prove its gallery photos belong to the event.
    matched=item.get("event_verified") and item.get("verified_event_id")==slug
    if matched and vision and relevance>=0.85 and vision.get("role")!="reject":
        caption=vision.get("description") or item.get("caption") or item.get("title") or ""
        archive_year=item.get("archive_year")
        if archive_year:
            if not str(slug[:4]).isdigit() or not 1 <= int(slug[:4])-int(archive_year) <= 3:return None
            if "archive" not in caption.lower():caption=f"Archive ({archive_year}): "+caption
        return {"event_id":slug,"category":category,"role":"hero" if category=="on-water" else "support","caption":caption,"verification":"vision_and_event_source","archive_year":archive_year,"source_url":item.get("source_url"),"credit":item.get("credit")}
    return None
def select_media(items,slug,root=None,issue=None):
    reviewed=[];seen=set()
    for item in items:
        from media_feedback import rejected
        if item.get("content_hash") and rejected(root or ROOT,slug,item["content_hash"]):continue
        if BANNED.search(" ".join(str(item.get(k) or "") for k in ("title","caption","category"))):continue
        evidence=image_evidence(item,slug,root,issue)
        if not evidence or evidence.get("category") not in {"on-water","prizegiving","portrait","ashore"}:continue
        key=item.get("content_hash") or item.get("local_path") or item.get("url")
        if key in seen:continue
        seen.add(key)
        copy=dict(item);copy["editorial"]=evidence
        reviewed.append(copy)
    heroes=[x for x in reviewed if x["editorial"].get("role")=="hero" and x["editorial"].get("category")=="on-water"]
    supports=[x for x in reviewed if x not in heroes]
    if not heroes:return supports[:2]
    # One sailing hero and two supports by default; a second hero requires explicit approval.
    return heroes[:1]+supports[:2]
def apply_article(article,issue,root=None):
    root=root or ROOT;slug=article.get("event_id") or article.get("id")
    original=[b for b in article.get("blocks",[]) if b.get("type")=="image"]
    selected=select_media(original,slug,root,issue)
    images=[]
    for idx,item in enumerate(selected):
        evidence=item.pop("editorial")
        block=dict(item);block["role"]="hero" if idx==0 and evidence["role"]=="hero" else "support"
        block["category"]=evidence["category"]
        block["verification"]=evidence["verification"]
        block["caption"]=evidence.get("caption") or block.get("caption") or ""
        block["alt"]=block["caption"].rstrip(".")
        for k in ("credit","source_url"):
            if evidence.get(k):block[k]=evidence[k]
        if evidence.get("focus") and re.fullmatch(r"(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%",str(evidence["focus"])):block["focus"]=evidence["focus"]
        images.append(block)
    body=[b for b in article.get("blocks",[]) if b.get("type")!="image" and not (b.get("type")=="paragraph" and re.search(r"the photograph with this report|the image accompanying",b.get("text",""),re.I))]
    texts=" ".join(b.get("text","") for b in body)
    for extra in rules(root).get("supplements",{}).get(slug,[]):
        if extra.get("verified") and extra["text"] not in texts:
            body.insert(next((i for i,b in enumerate(body) if b.get("type")=="results"),len(body)),{"type":"paragraph","text":extra["text"],"source_urls":extra["sources"]})
            article["sources"]=list(dict.fromkeys(article.get("sources",[])+extra["sources"]))
            article["third_party"]=True
            article["needs_external"]=False
    article["blocks"]=images+body
    article["media_layout"]="hero-support"
    hero=next((b for b in images if b["role"]=="hero"),None)
    article["hero_image"]={k:hero.get(k) for k in ("url","source_url","caption","credit","verification","focus")} if hero else None
    if not hero:
        path=root/"issues"/issue/"sources"/(slug+"-media-fallback.json")
        if path.exists():
            evidence=json.loads(path.read_text())
            if evidence.get("quick_archive") and evidence.get("allow_text_only") and quick_archive(issue,root,evidence.get("event_end")):
                article["media_exception"]={"reason":"quick_archive_no_easy_verified_photo","evidence":str(path.relative_to(root)),"quick_attempted":True,"deep_search_waived_by_user":True}
            elif evidence.get("allow_text_only") and evidence.get("current_attempted") and evidence.get("archive_attempted"):
                article["media_exception"]={"reason":"no_verified_event_photo","evidence":str(path.relative_to(root)),"current_attempted":True,"archive_attempted":True}
    return article
def is_local_sas_report(article):
    """A full SailingSA result, not an international brief or an unscored listing."""
    if not isinstance(article, dict) or article.get("type") != "regatta_report":
        return False
    if article.get("review_status") == "verified_external" or article.get("international") is True:
        return False
    event_id = str(article.get("event_id") or article.get("id") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+", event_id):
        return False
    try:
        return int(article.get("entries") or 0) > 0
    except (TypeError, ValueError):
        return False

def local_sas_reports(reports):
    local = [article for article in reports or [] if is_local_sas_report(article)]
    return sorted(local, key=lambda article: int(article.get("entries") or 0), reverse=True)

def local_report_rank(article):
    try:
        entries = int(article.get("entries") or 0)
    except (TypeError, ValueError):
        entries = 0
    return (1 if is_local_sas_report(article) else 0, entries)

def order_articles_for_hero(data):
    """Largest local SAS result leads. A bigger international event stays an article."""
    articles = list(data.get("articles") or [])
    feature = [article for article in articles if article.get("type") == "feature"]
    reports = [article for article in articles if article.get("type") == "regatta_report"]
    rest = [article for article in articles if article.get("type") not in {"feature", "regatta_report"}]
    local = local_sas_reports(reports)
    local_ids = {id(article) for article in local}
    others = sorted(
        (article for article in reports if id(article) not in local_ids),
        key=lambda article: int(article.get("entries") or 0),
        reverse=True,
    )
    data["articles"] = feature + local + others + rest
    return data

def issue_hero(reports):
    top = next(iter(local_sas_reports(reports)), None)
    return (dict(top["hero_image"], event_id=top.get("event_id")) if top and top.get("hero_image") else None)

def validate_weekly_hero(data):
    """The largest local SAS result owns the hero. No photograph does not block publication."""
    order_articles_for_hero(data)
    reports = [article for article in data.get("articles", []) if article.get("type") == "regatta_report"]
    if not reports:
        raise ValueError("No full event reports for weekly hero selection")
    local = local_sas_reports(reports)
    feature = next((article for article in data["articles"] if article.get("type") == "feature"), {})
    if not local:
        if (feature.get("hero_image") or {}).get("url"):
            raise ValueError("Edition without a local SAS result must not borrow another event photograph")
        feature.pop("hero_image", None)
        return None
    top = local[0]
    owner = top.get("event_id") or top.get("id")
    if reports[0].get("event_id") != owner:
        raise ValueError("Largest local SAS event must lead the full reports")
    hero = top.get("hero_image") or {}
    if not hero.get("url"):
        if (feature.get("hero_image") or {}).get("url"):
            raise ValueError("Text-only edition must not borrow another event photograph")
        feature.pop("hero_image", None)
        return owner
    selected = feature.get("hero_image") or {}
    if selected.get("url") != hero["url"] or selected.get("event_id") != owner:
        raise ValueError("Weekly hero must match the largest local SAS event with verified results")
    first = next((block for block in top.get("blocks", []) if block.get("type") == "image"), {})
    if first.get("url") != hero["url"] or first.get("role") != "hero":
        raise ValueError("Local SAS hero must be the first photograph on the edition page")
    return owner
