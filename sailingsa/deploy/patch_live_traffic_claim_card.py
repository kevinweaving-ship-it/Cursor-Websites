#!/usr/bin/env python3
"""Fix /traffic Claim / sign-up card: pause 503 presented as 'failed'.

claim-attempts was the only lean traffic API not intercepted by
_lean_traffic_route_override, so it hit the public-priority shed and
returned {paused:true} with no ok/error. Overview/live/top already
bypass that shed. Route claim-attempts the same way, retry paused
JSON, and stop the KPI from hanging on '…'.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

API_REPLACEMENTS = [
    (
        """        if path == "/traffic/api/bucket":
            return lean_traffic_api_bucket(request)
        if path in (""",
        """        if path == "/traffic/api/bucket":
            return lean_traffic_api_bucket(request)
        if path == "/traffic/api/claim-attempts":
            return lean_traffic_api_claim_attempts(request)
        if path in (""",
    ),
    (
        """  function fetchJson(url){
    return fetch(url,{credentials:"same-origin",cache:"no-store"}).then(function(r){
      if(r.status===307||r.status===401||r.status===403) throw new Error("Login / admin required");
      return r.json();
    });
  }""",
        """  function fetchJson(url){
    function once(){
      return fetch(url,{credentials:"same-origin",cache:"no-store"}).then(function(r){
        if(r.status===307||r.status===401||r.status===403) throw new Error("Login / admin required");
        return r.json();
      });
    }
    function withRetry(left){
      return once().then(function(d){
        if(d && d.paused && left > 0){
          var ms = Math.min(Math.max(Number(d.retry_after_sec)||2, 1), 3) * 1000;
          return new Promise(function(res){ setTimeout(res, ms); }).then(function(){ return withRetry(left-1); });
        }
        return d;
      });
    }
    return withRetry(3);
  }""",
    ),
    (
        """      if(!d || !d.ok) throw new Error((d && d.error) || "failed");""",
        """      if(!d || !d.ok) throw new Error((d && (d.error || d.detail)) || (d && d.paused ? "paused — retry shortly" : "failed"));""",
    ),
    (
        """      fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(cd){
        if(!cd || !cd.ok) return;
        var nTry=Number(cd.attempt_count||0), nOk=Number(cd.success_count||0), nFail=Number(cd.fail_count||0), nLeft=Number(cd.left_count||0);
        if($("kClaim")) $("kClaim").textContent=String(nTry);
        if($("kClaimSub")) $("kClaimSub").textContent=nOk+" members · "+nFail+" blocked · "+nLeft+" left · "+rangeLabel();""",
        """      fetchJson("/traffic/api/claim-attempts?range="+encodeURIComponent(RANGE)).then(function(cd){
        if(!cd || !cd.ok){
          var why = (cd && (cd.error || cd.detail)) || (cd && cd.paused ? "paused — tap to retry" : "could not load");
          if($("kClaim")) $("kClaim").textContent="—";
          if($("kClaimSub")) $("kClaimSub").textContent=String(why);
          var box0=$("claimFunnelBody");
          if(box0) box0.innerHTML="<p class='err'>"+esc(String(why))+"</p>";
          return;
        }
        var nTry=Number(cd.attempt_count||0), nOk=Number(cd.success_count||0), nFail=Number(cd.fail_count||0), nLeft=Number(cd.left_count||0);
        if($("kClaim")) $("kClaim").textContent=String(nTry);
        if($("kClaimSub")) $("kClaimSub").textContent=nOk+" members · "+nFail+" blocked · "+nLeft+" left · "+rangeLabel();""",
    ),
    (
        """        }catch(eClaim){}
      }).catch(function(){});
      $("kLiveSub").textContent="total online · last "+(o.live_minutes||15)+" min window"+(o.live_signed?(" · "+o.live_signed+" signed"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"");""",
        """        }catch(eClaim){}
      }).catch(function(eCd){
        if($("kClaim")) $("kClaim").textContent="—";
        if($("kClaimSub")) $("kClaimSub").textContent=String((eCd && eCd.message) || "could not load");
        var box1=$("claimFunnelBody");
        if(box1) box1.innerHTML="<p class='err'>"+esc(String((eCd && eCd.message) || "could not load"))+"</p>";
      });
      $("kLiveSub").textContent="total online · last "+(o.live_minutes||15)+" min window"+(o.live_signed?(" · "+o.live_signed+" signed"):"")+(o.quarantine_ips?(" · "+o.quarantine_ips+" bots quarantined"):"");""",
    ),
]


def apply(path: Path, reps: list) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(reps, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    api = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    apply(api, API_REPLACEMENTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
