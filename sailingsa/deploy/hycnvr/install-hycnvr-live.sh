#!/bin/bash
# Install isolated HYC NVR producer on THIS machine (run on live as root).
# Does not patch Voelklip hikpoc camera fetch (D49460413 garage/workshop/pool/driveway).
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
HYC_DIR=/opt/hycnvr
HIKPOC=/opt/hikpoc
YAML="$HIKPOC/go2rtc.yaml"
STAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$HYC_DIR/out"
chmod 700 "$HYC_DIR" "$HYC_DIR/out"
install -m 0755 "$SCRIPT_DIR/bridge_hyc.py" "$HYC_DIR/bridge_hyc.py"
install -m 0755 "$SCRIPT_DIR/wait_hevc_vps.py" "$HYC_DIR/wait_hevc_vps.py"

if grep -q 'HIK_PS_CLEAR' "$HIKPOC/bridge_cam.py" 2>/dev/null; then
  if [[ -f "$HIKPOC/bridge_cam.py.bak.psclear" ]]; then
    cp -a "$HIKPOC/bridge_cam.py" "$HIKPOC/bridge_cam.py.bak.hycpatch_$STAMP"
    cp -a "$HIKPOC/bridge_cam.py.bak.psclear" "$HIKPOC/bridge_cam.py"
    echo "restored $HIKPOC/bridge_cam.py from bak.psclear"
  fi
fi
if grep -q 'HIK_PS_CLEAR' "$HIKPOC/bridge_cam.py"; then
  echo "ERROR: shared bridge_cam.py still has HIK_PS_CLEAR" >&2
  exit 1
fi

if [[ ! -f "$HYC_DIR/.env" ]]; then
  python3 - "$HIKPOC/.env" "$HYC_DIR/.env" <<'PY'
import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
keys = {}
for line in src.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        keys[k.strip()] = v
out = [
    "HIK_ACCOUNT=" + keys.get("HIK_ACCOUNT", ""),
    "HIK_PASSWORD=" + keys.get("HIK_PASSWORD", ""),
    "HIK_HOST=" + keys.get("HIK_HOST", "api.hik-connect.com"),
    "HIK_MEDIA_KEY=" + (keys.get("HYC_NVR_PASSWORD") or keys.get("HIK_MEDIA_KEY") or ""),
    "HYC_NVR_PASSWORD=" + (keys.get("HYC_NVR_PASSWORD") or keys.get("HIK_MEDIA_KEY") or ""),
    "HYC_NVR_SERIAL=D23413606",
    "HYC_NVR_CHANNEL=5",
    "HIK_PS_CLEAR=0",
]
dst.write_text("\n".join(out) + "\n")
dst.chmod(0o600)
print("wrote", dst)
PY
fi

python3 - "$YAML" "$STAMP" <<'PY'
from pathlib import Path
import sys
yaml, stamp = Path(sys.argv[1]), sys.argv[2]
text = yaml.read_text()
bak = yaml.with_name(yaml.name + ".bak.hycnvr_" + stamp)
bak.write_text(text)
line = (
    '  hyc: exec:bash -c "trap \'kill 0\' EXIT TERM INT; cd /opt/hycnvr && '
    '/opt/hikpoc/venv/bin/python bridge_hyc.py D23413606 5 hevc main 2>>/opt/hycnvr/out/bridge_hyc.log | '
    '/opt/hikpoc/venv/bin/python wait_hevc_vps.py | /opt/hikpoc/bin/ffmpeg -hide_banner -loglevel error '
    '-fflags nobuffer+genpts -flags low_delay -err_detect ignore_err -ec favor_inter -probesize 500000 '
    '-analyzeduration 500000 -f hevc -i pipe:0 -vf scale=1280:-2 -r 20 -vsync cfr -c:v libx264 -preset veryfast '
    '-tune zerolatency -profile:v main -pix_fmt yuv420p -crf 20 -maxrate 2500k -bufsize 4000k -g 40 '
    '-muxdelay 0 -muxpreload 0 '
    '-rtsp_transport tcp -f rtsp {output}"'
)
out = []
changed = False
for raw in text.splitlines():
    if raw.lstrip().startswith("hyc:"):
        out.append(line)
        changed = True
    else:
        out.append(raw)
if not changed:
    raise SystemExit("hyc: stream line not found in go2rtc.yaml")
for name in ("garage:", "workshop:", "pool:", "driveway:"):
    if not any(r.lstrip().startswith(name) and "D49460413" in r and "/opt/hikpoc" in r for r in out):
        raise SystemExit("refusing to write yaml: %s Voelklip line missing/changed" % name)
    if any(r.lstrip().startswith(name) and "hycnvr" in r for r in out):
        raise SystemExit("refusing to write yaml: Voelklip %s pointed at hycnvr" % name)
if any("D23413606" in r and "/opt/hikpoc &&" in r for r in out):
    raise SystemExit("refusing to write yaml: HYC still on hikpoc fetch")
yaml.write_text("\n".join(out) + "\n")
print("patched", yaml, "backup", bak)
PY

echo "install-hycnvr-live: ok"
