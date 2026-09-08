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

## Stanford compliance

| Cam | Serial | Allowed videoLevel | Forbidden |
|---|---|---|---|
| Front Garage | `BF4277866` | **2** | 3, 4, 6 |
| EB5 | `BF4277838` | **2** | 3, 4, 6 |

Setter: `arial/stanford/set_ezviz_video_level.py` (Stanford serials only).

Cursor rule: `.cursor/rules/ezviz-bing-gold.mdc`.
