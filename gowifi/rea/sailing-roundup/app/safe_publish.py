#!/usr/bin/env python3
"""Build in isolation, validate, then replace only the requested issue."""
from __future__ import annotations
import argparse,hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent

def validate(root,issue):
    from gates import require_publishable
    require_publishable(issue, root=root)
    out=root/"public/issues"/issue
    data=json.loads((out/"issue.json").read_text())
    articles=data.get("articles",[]);ids=[a["event_id"] for a in articles]
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate event articles")
    reports=[a for a in articles if a["type"]=="regatta_report"]
    weekend=json.loads((root/"issues"/issue/"sources/events-weekend.json").read_text())
    events=weekend.get("events") or []
    expected={e["regatta_id"] for e in events if e.get("regatta_id")}
    expected |= {s for s in (weekend.get("slugs") or []) if s}
    report_ids={a["event_id"] for a in reports}
    if not expected <= report_ids:raise ValueError("Missing scored event")
    hashes=set()
    for a in reports:
        cluster=json.loads((root/"issues"/issue/"sources"/(a["event_id"]+"-cluster.json")).read_text())
        if any(not s.get("verification",{}).get("accepted") for s in cluster["articles"]):raise ValueError("Unverified source")
        if len(a.get("citations",[]))!=len({x["url"].rstrip("/") for x in a.get("citations",[])}):raise ValueError("Duplicate citations")
        from evidence_pipeline import other_event_conflict
        facts={"slug":a.get("event_id") or a.get("id") or "","title":a.get("class_name") and "" or "","event_name":a.get("headline") or ""}
        slug=str(facts["slug"])
        for cite in a.get("citations") or []:
            if other_event_conflict(cite, {"slug":slug,"title":a.get("headline") or slug,"url":"https://sailingsa.co.za/regatta/"+slug}):
                raise ValueError("Citation belongs to another event")
        for b in a["blocks"]:
            if b["type"]=="paragraph":
                if re.search(r"\[\d+\]",b.get("text") or ""):raise ValueError("Cite marks in public copy")
                if other_event_conflict({"url":"","title":"","body":b.get("text") or ""}, {"slug":slug,"title":a.get("headline") or slug}, require_identity=False):
                    raise ValueError("Article quotes another event")
            if b["type"]=="results" and len(b["rows"])>3:raise ValueError("Article table must be podium only")
            if b["type"]=="image":
                path=(out/b["url"]).resolve()
                if not path.is_relative_to(out.resolve()) or not path.is_file():raise ValueError("Missing image")
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in hashes:raise ValueError("Repeated photograph")
                hashes.add(digest)
                if other_event_conflict({"url":b.get("source_url") or "","title":b.get("caption") or ""}, {"slug":slug,"title":a.get("headline") or slug}):
                    raise ValueError("Photograph belongs to another event")
    if not (out/"index.html").is_file():raise ValueError("Missing HTML")
    pdf=out/"edition.pdf"
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):raise ValueError("Missing PDF")
    return {"articles":len(reports),"photographs":len(hashes),"issue":issue,"validation":"passed"}

def publish(issue,test=False):
    if test:issue="2026-09-28"
    if not issue:
        import datetime as dt
        from zoneinfo import ZoneInfo
        today=dt.datetime.now(ZoneInfo("Africa/Johannesburg")).date()
        issue=(today-dt.timedelta(days=today.weekday())).isoformat()
    work=ROOT/".builds";work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=issue+"-",dir=work) as temp:
        stage=pathlib.Path(temp)
        shutil.copytree(ROOT/"app",stage/"app",ignore=shutil.ignore_patterns("__pycache__"))
        for relative in ("issues/"+issue,"public/issues/"+issue):
            source=ROOT/relative
            if source.exists():shutil.copytree(source,stage/relative)
        # Never let a failed render pass validation using the previous edition's PDF.
        for filename in ("edition.pdf","index.html","issue.json"):
            (stage/"public/issues"/issue/filename).unlink(missing_ok=True)
        # An existing source registry is a discovery aid, not publication evidence.
        if (ROOT/"data").is_dir():shutil.copytree(ROOT/"data",stage/"data",ignore=shutil.ignore_patterns("*.log"))
        subprocess.run([sys.executable,str(stage/"app/publish_weekend.py"),"--monday",issue,"--rebuild"],check=True,timeout=600)
        result=validate(stage,issue)
        backup=ROOT/"backups"/(issue+"-"+str(__import__("time").time_ns()));backup.mkdir(parents=True)
        replaced=[]
        try:
            for relative in ("issues/"+issue,"public/issues/"+issue):
                destination=ROOT/relative;destination.parent.mkdir(parents=True,exist_ok=True)
                saved=backup/relative;saved.parent.mkdir(parents=True,exist_ok=True)
                if destination.exists():os.replace(destination,saved)
                try:os.replace(stage/relative,destination)
                except Exception:
                    if saved.exists():os.replace(saved,destination)
                    raise
                replaced.append((destination,saved))
        except Exception:
            for dest,saved in reversed(replaced):
                shutil.rmtree(dest)
                if saved.exists():os.replace(saved,dest)
            raise
        from landing import write_public_index
        write_public_index()
        (ROOT/"data").mkdir(exist_ok=True)
        (ROOT/"data/last-success.json").write_text(json.dumps(result,indent=2))
        return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--monday");p.add_argument("--test-weekend",action="store_true");args=p.parse_args()
    print(json.dumps(publish(args.monday,args.test_weekend),indent=2))
