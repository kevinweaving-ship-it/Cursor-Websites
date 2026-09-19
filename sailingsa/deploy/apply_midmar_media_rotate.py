#!/usr/bin/env python3
"""Install Midmar 90° media rotate + persist last angle."""
from pathlib import Path
import shutil
import time

MARK = "MIDMAR_MEDIA_ROTATE_v1"
SRC = Path("/tmp/midmar-media-rotate.js")
DEST = Path("/var/www/sailingsa/js/midmar-media-rotate.js")
MEDIA = Path("/var/www/sailingsa/js/midmar-live-media.js")
MM = Path("/var/www/sailingsa/sailingsa/backend/mm_event_clips.py")
API = Path("/var/www/sailingsa/api/api.py")

MM_FN = '''

def set_clip_rotation(rid: str, clip_id: str, rotation: int, static_dir: Path) -> dict:
    """Persist 0/90/180/270 on a clip. Does not invent media."""
    rot = int(rotation or 0)
    rot = ((rot % 360) + 360) % 360
    rot = int(round(rot / 90.0) * 90) % 360
    if rot not in (0, 90, 180, 270):
        rot = 0
    data = load_or_seed(rid, static_dir)
    videos = list(data.get("videos") or [])
    found = None
    for v in videos:
        if str(v.get("id") or "") == str(clip_id):
            v["rotation"] = rot
            found = v
            break
    if found is None:
        raise ValueError("clip not found")
    save_clips(rid, static_dir, videos)
    return found
'''

CLIP_OLD = '''        "width": w,
        "height": h,
        "file_sha256": digest,
    }'''
CLIP_NEW = '''        "width": w,
        "height": h,
        "rotation": int(rotation or 0) if int(rotation or 0) in (0, 90, 180, 270) else 0,
        "file_sha256": digest,
    }'''

SIG_OLD = '''    width: int,
    height: int,
    static_dir: Path,
) -> dict:'''
SIG_NEW = '''    width: int,
    height: int,
    static_dir: Path,
    rotation: int = 0,
) -> dict:'''

POST_OLD = '''    width: int = Form(0),
    height: int = Form(0),
):
    """Super Admin: drop a photo/video onto the event MM card."""'''
POST_NEW = '''    width: int = Form(0),
    height: int = Form(0),
    rotation: int = Form(0),
):
    """Super Admin: drop a photo/video onto the event MM card."""'''

CALL_OLD = '''            width=width,
            height=height,
            static_dir=Path(_static_dir()),
        )'''
CALL_NEW = '''            width=width,
            height=height,
            static_dir=Path(_static_dir()),
            rotation=rotation,
        )'''

PATCH = r'''

@app.patch("/api/super-admin/regatta/{regatta_id}/mm-clips/{clip_id}")
async def api_super_admin_mm_clips_rotate(request: Request, regatta_id: str, clip_id: str):
    """Super Admin: save last 90° rotation for a Midmar clip."""
    from sailingsa.backend import mm_event_clips as _mm_clips

    if not _session_role_is_super_admin(request):
        raise HTTPException(status_code=403, detail="super_admin only")
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        clip = _mm_clips.set_clip_rotation(
            rid=regatta_id,
            clip_id=clip_id,
            rotation=int((body or {}).get("rotation") or 0),
            static_dir=Path(_static_dir()),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "clip": clip, "videos": _mm_clips.public_payload(regatta_id, Path(_static_dir()))["videos"]}
'''


def main() -> None:
    if not SRC.is_file():
        raise SystemExit("MISSING_SRC")
    src = SRC.read_text()
    if "mmApplyClipRotations" not in src:
        raise SystemExit("SRC_BAD")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("JS_OK", DEST, DEST.stat().st_size)

    ts = time.strftime("%Y%m%d_%H%M%S")

    mm = MM.read_text()
    if "def set_clip_rotation" not in mm:
        if CLIP_OLD not in mm or SIG_OLD not in mm:
            raise SystemExit("MM_ANCHOR_MISSING")
        bak = MM.with_name(f"mm_event_clips.py.bak.rot.{ts}")
        shutil.copy2(MM, bak)
        print("BACKUP_MM", bak)
        mm = mm.replace(SIG_OLD, SIG_NEW, 1)
        mm = mm.replace(CLIP_OLD, CLIP_NEW, 1)
        mm = mm.rstrip() + MM_FN
        MM.write_text(mm)
        print("MM_OK")
    else:
        print("MM_ALREADY")

    api = API.read_text()
    if "api_super_admin_mm_clips_rotate" not in api:
        if POST_OLD not in api or CALL_OLD not in api:
            raise SystemExit("API_UPLOAD_ANCHOR_MISSING")
        api = api.replace(POST_OLD, POST_NEW, 1)
        api = api.replace(CALL_OLD, CALL_NEW, 1)
        close = (
            '    return {"ok": True, "clip": clip, "videos": _mm_clips.public_payload(regatta_id, Path(_static_dir()))["videos"]}\n'
            '\n'
            '@app.get("/api/admin/hub/assets")'
        )
        close_new = (
            '    return {"ok": True, "clip": clip, "videos": _mm_clips.public_payload(regatta_id, Path(_static_dir()))["videos"]}\n'
            + PATCH
            + '\n@app.get("/api/admin/hub/assets")'
        )
        if close not in api:
            raise SystemExit("API_CLOSE_ANCHOR_MISSING")
        api = api.replace(close, close_new, 1)
        print("API_PATCH_OK")
    else:
        print("API_PATCH_ALREADY")

    old_tag = (
        "mm_card_script = '<script src=\"/js/midmar-live-media.js?v=midmarwx41\" defer></script>"
        "<script src=\"/js/midmar-leaderboard.js?v=mmlb6\" defer></script>'"
    )
    new_tag = (
        "mm_card_script = '<script src=\"/js/midmar-live-media.js?v=midmarwx42\" defer></script>"
        "<script src=\"/js/midmar-leaderboard.js?v=mmlb6\" defer></script>"
        "<script src=\"/js/midmar-media-rotate.js?v=mmrot1\" defer></script>'"
    )
    if old_tag in api:
        api = api.replace(old_tag, new_tag)
        print("API_TAG_OK")
    elif "midmar-media-rotate.js" in api:
        print("API_TAG_ALREADY")
    else:
        api2 = api.replace("midmar-live-media.js?v=midmarwx41", "midmar-live-media.js?v=midmarwx42")
        if "midmar-media-rotate.js" not in api2 and "midmar-leaderboard.js?v=mmlb6" in api2:
            api2 = api2.replace(
                "<script src=\"/js/midmar-leaderboard.js?v=mmlb6\" defer></script>",
                "<script src=\"/js/midmar-leaderboard.js?v=mmlb6\" defer></script>"
                "<script src=\"/js/midmar-media-rotate.js?v=mmrot1\" defer></script>",
            )
        api = api2
        print("API_TAG_FALLBACK")

    if api != API.read_text():
        API.write_text(api)
        print("API_WRITE")

    media = MEDIA.read_text()
    if MARK in media:
        print("MEDIA_ALREADY")
        return
    bakm = MEDIA.with_name(f"midmar-live-media.js.bak.rot.{ts}")
    shutil.copy2(MEDIA, bakm)
    print("BACKUP_MEDIA", bakm)

    media = media.replace('JS_VER = "midmarwx41"', 'JS_VER = "midmarwx42"', 1)
    media = media.replace(
        'loadScript("/js/midmar-leaderboard.js?v=mmlb6");',
        'loadScript("/js/midmar-leaderboard.js?v=mmlb6");\n    loadScript("/js/midmar-media-rotate.js?v=mmrot1");',
        1,
    )
    media = media.replace(
        'if (typeof window.mmLiptonReelsReplaceVideos === "function") {\n      window.mmLiptonReelsReplaceVideos(videos);\n    }',
        'if (typeof window.mmLiptonReelsReplaceVideos === "function") {\n      window.mmLiptonReelsReplaceVideos(videos);\n    }\n'
        '    if (typeof window.mmApplyClipRotations === "function") {\n      window.mmApplyClipRotations(videos);\n    }',
        1,
    )
    media = media.replace(
        'pending = { file: null, width: 0, height: 0 };',
        'pending = { file: null, width: 0, height: 0, rotation: 0 };',
        1,
    )
    media = media.replace(
        'pending = { file: f, width: 0, height: 0 };',
        'pending = { file: f, width: 0, height: 0, rotation: 0 };',
        1,
    )
    media = media.replace(
        'fd.append("height", String(h));',
        'fd.append("height", String(h));\n          fd.append("rotation", String((pending && pending.rotation) || window.__mmSaRotation || 0));',
        1,
    )
    sa_old = '\'<button type="button" class="midmar-mm-sa-save" data-mm-sa-save>Save to card</button>\' +'
    sa_new = (
        '\'<button type="button" class="midmar-mm-sa-rot" data-mm-sa-rot title="Rotate 90 degrees">Rotate 90°</button>\' +\n'
        '      \'<button type="button" class="midmar-mm-sa-save" data-mm-sa-save>Save to card</button>\' +'
    )
    if sa_old in media:
        media = media.replace(sa_old, sa_new, 1)
        print("SA_BTN_OK")
    bind_old = '    if (save) {\n      save.addEventListener("click", function () {'
    bind_new = (
        '    var rotBtn = sa.querySelector("[data-mm-sa-rot]");\n'
        '    if (rotBtn) {\n'
        '      rotBtn.addEventListener("click", function (e) {\n'
        '        e.preventDefault();\n'
        '        e.stopPropagation();\n'
        '        pending.rotation = ((pending.rotation || 0) + 90) % 360;\n'
        '        window.__mmSaRotation = pending.rotation;\n'
        '        rotBtn.textContent = "Rotate " + pending.rotation + "°";\n'
        '        var vis = preview && preview.querySelector("img, video");\n'
        '        if (vis) vis.style.transform = "rotate(" + pending.rotation + "deg)";\n'
        '        if (drop && pending.width && pending.height) {\n'
        '          var pw = pending.width, ph = pending.height;\n'
        '          if (pending.rotation === 90 || pending.rotation === 270) { var t = pw; pw = ph; ph = t; }\n'
        '          setDropOrient(drop, pw, ph);\n'
        '        }\n'
        '      });\n'
        '    }\n'
        '    if (save) {\n      save.addEventListener("click", function () {'
    )
    if bind_old in media:
        media = media.replace(bind_old, bind_new, 1)
        print("SA_BIND_OK")
    if MARK not in media:
        media = media.replace(
            "  var JS_VER = ",
            "  // " + MARK + "\n  var JS_VER = ",
            1,
        )
    MEDIA.write_text(media)
    print("MEDIA_OK", MEDIA.stat().st_size)


if __name__ == "__main__":
    main()
