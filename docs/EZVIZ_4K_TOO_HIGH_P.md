# EZVIZ 4K / too-high P — why Stanford does not load

Front Garage is on the **right protocol** (RTP HEVC decrypt → 640 out). It still looks gray/green because the **camera encode is still 4K-class**. Asking `stream=2` on the VTM URL does not drop P.

## Live facts (pagelist, this dive)

| Cam | Type | videoLevel now | Meaning (official) | What we actually get |
|---|---|---|---|---|
| Bing Carport | IPC C8C | **0** | Fluent | Clear MPEG-PS, 640, Bing gold |
| Front Garage | BatteryCamera | **4** | 极清 (extreme) | Encrypted RTP HEVC, IDR ~97–154 KB |
| EB5 (off) | BatteryCamera | **6** | **4K** | Same RTP class |

Official EZUIKit levels ([videoLevelList.md](https://github.com/Ezviz-OpenBiz/EZUIKit-JavaScript-npm/blob/master/videoLevelList.md)):

`0` fluent · `1` SD · `2` HD · `3` ultra · `4` extreme · `5` 3K · `6` 4K

`streamTypeIn` is only **1 = main** or **2 = sub**. On their C6Wi example, **level 2 is the substream row**; 3/4/6 are all **main**, and 6 is 4K (`maxBitRate: 4096`).

## Why `stream=2` / `videoLevel=2` on the URL does nothing

EZ official, same file:

- If the device **did not report a substream**, the SDK assumes **no sub**. The fallback list is **all main**. Switching “quality” then **does not change the stream**.
- If the requested `level` is **not in the device list**, take-stream uses the **last set level**.
- Quality switch that *does* work **rewrites the device encode** (resolution / fps). A URL query is not that.

EZ official SDK FAQ ([setVideoLevel](https://support.ezviz.com/faq/428)):

1. `setVideoLevel(serial, channel, videoLevel)`
2. **Stop** live (`stopRealPlay`)
3. **Start** live again (`startRealPlay`)

We never call `setVideoLevel`. We only tack `stream` / `videoLevel` / `qn` onto the VTM URL. Pagelist still shows FG **4** and EB5 **6**. IDRs stay 4K-sized. ffmpeg `scale=640` only shrinks a broken decode.

`pyezvizapi` has **no** `setVideoLevel`. Closest is `set_dev_config_kv(..., "videoLevel", 2)`, which is what `set_ezviz_video_level.py` already does. `set_video_enc` is **encryption on/off**, not quality. Do not use it.

## Why the setter returns 2009

Home Assistant + pyezviz ([core#84577](https://github.com/home-assistant/core/issues/84577)):

`meta.code` **2009** = `设备网络异常,请检查设备网络或者重试`

EZVIZ FAQ [“Device is busy”](https://support.ezviz.com/faq/article/What-does-the-error-message-Device-is-busy-mean): max **simultaneous connections**. Log out other viewers or power-cycle.

Stanford uplink is thin. App + go2rtc + quality-set at once = 2009. That is why `drop_to_bing_level()` on live start stalls and must stay off the start path.

## Why 640 JPEG is still gray/green

Hikvision/EZVIZ NAL encrypt is **AES-128-ECB, first 4096 only** (Voëlklip `bridge_cam.py` / our RTP bridge). On a **small** IDR that is enough. On a **4K** IDR (~100 KB+) you get a **sliver of real picture + gray/green**. Whole-NAL decrypt is worse (destroys the clear tail). This is not the MPEG player.

[RenierM26/pyEzvizApi](https://github.com/RenierM26/pyEzvizApi): `--decrypt-video` is for **MPEG-PS** battery dumps (Bing-shaped). Stanford VTM is **RTP**, not PS. Official `stream dump --decrypt-video` already gave **0 bytes** here.

[LethalEthan/LE-EZVIZ-VS](https://github.com/LethalEthan/LE-EZVIZ-VS): clear MPEG-PS and **clear** H.265 RTP work. Encrypted RTP is explicitly unfinished.

## What Git / HA / Reddit actually do for “4K won’t load”

Consensus is **do not pull cloud 4K for a dashboard card**:

1. **Phone / EZVIZ Studio:** set live quality to Fluent / HD and leave it. App “Resolution” on LAN preview often **does not** change the encode ([H8c Pro 4K + HA](https://raspberry.tips/en/smart-home/ezviz-h8c-pro-4k-home-assistant-review)).
2. **LAN RTSP substream** (HA gold): `/Streaming/Channels/102`, not `101`. [ha-ezviz](https://github.com/RenierM26/ha-ezviz) default path is **102**. [HA ezviz docs](https://www.home-assistant.io/integrations/ezviz/).
3. **H.265 in the browser fails** — transcode to H.264 in go2rtc (we already do that *after* decrypt). HA threads: keep main H.265 for record, **sub H.264 ~640** for live ([ONVIF/H265](https://community.home-assistant.io/t/onvif-integration-and-h265/261057), [C8C + Studio STD_H264](https://community.home-assistant.io/t/ezviz-c8c-doesnt-work-on-ha/356396/20)).
4. Battery cameras often have **no advertised RTSP** in `supportExt` (FG/EB5/Bing pagelist: no `rtsp` flag). Cloud VTM is the only path from this server unless someone enables LAN RTSP and the server can reach that LAN.

## What will actually drop P (ordered)

1. **Human, in the EZVIZ app, on Front Garage only:** set quality to **Fluent or HD (0 or 2)**, close other viewers, then reload `/stanford/`. This is the official set+restart. Cloud setter cannot do it while 2009.
2. **Idle cloud setter (code):** stop the Stanford go2rtc consumer (do not knock Bing/VK if possible), wait until nobody is connected, `set_dev_config_kv(FG, 1, "videoLevel", 2)`, confirm pagelist `videoLevel==2`, then start RTP again. If still 2009, back to (1).
3. **LAN 102** only if the live box can reach the camera LAN and RTSP is enabled. This server almost certainly cannot.
4. **Do not:** put Stanford back on Bing MPEG; call quality-set on every live start; decrypt the whole 4K NAL; turn off encryption; turn EB5 on.

## Bottom line

Too-high P is a **device encode stuck on 4/6**, not a wrong player. RTP + 640 scale is correct. Until Front Garage’s **pagelist `videoLevel` is 2 or lower**, 4096 decrypt cannot make a clean Bing-class picture.
