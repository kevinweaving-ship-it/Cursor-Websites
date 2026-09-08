# EZVIZ Bing gold

Live EZVIZ on Arial is **whatever Bing Carport does**. That is the rule. 4K does not comply.

## Gold (do not change)

| Piece | Bing Carport |
|---|---|
| Stream name | `carport_test` |
| Serial | `BA3858958` |
| Source | `/opt/ezvizpoc/bridge_ezviz.sh BA3858958` |
| ffmpeg | hikpoc `-f mpeg -vf scale=640:-2 -r 12` baseline h264 → go2rtc RTSP |
| Card | thumb + EZVIZ overlay + `video-stream` `mse,mjpeg` |
| videoLevel | **0** (C8C also lists 1/2/3 — live stays on 0) |

## Limits

- Output: **640×360-class**, 12 fps. Not 1080p. Not 4K.
- videoLevel: Bing-class. EB5 lowest listed is **2**. **Never 4 or 6** (those are 4K-class on Stanford).
- Do not start a second EZVIZ dump until the hero card is actually live (Stanford uplink).
- Do not edit `carport_test` unless the user names Bing in that request.

## Stanford live (not Bing MPEG)

Stanford Front Garage sends **RTP HEVC**, not MPEG-PS. Bing's `-f mpeg` player will never frame it.

| Piece | Stanford Front Garage |
|---|---|
| Stream name | `stanford_front_garage` |
| Serial | `BF4277866` |
| Source | `/opt/ezvizpoc/bridge_ezviz_rtp.py BF4277866` |
| ffmpeg | hikpoc `-f hevc -vf scale=640:-2 -r 12` baseline h264 → go2rtc RTSP |
| Card | same Bing EZVIZ card (thumb + overlay + `mse,mjpeg`) |
| EB5 | **off** |

Do **not** call `drop_to_bing_level()` on live start (EZVIZ 2009 stalls first frame). Request `stream=2` / `videoLevel=2` on the VTM URL only.

## Stanford compliance

| Cam | Serial | Allowed videoLevel | Forbidden |
|---|---|---|---|
| Front Garage | `BF4277866` | **2** | 3, 4, 6 |
| EB5 | `BF4277838` | **2** (disabled) | 3, 4, 6 |

Setter: `arial/stanford/set_ezviz_video_level.py` (Stanford serials only). Not on the live start path.

**4K / too-high P:** URL `stream=2` does not drop encode. FG pagelist is **4**, EB5 is **6**. Gray/green 640 JPEG = 4096 decrypt of a 4K IDR. Full dive: **`docs/EZVIZ_4K_TOO_HIGH_P.md`**.

Cursor rule: `.cursor/rules/ezviz-bing-gold.mdc`.
