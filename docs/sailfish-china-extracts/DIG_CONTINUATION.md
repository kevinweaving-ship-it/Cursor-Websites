# Sailfish dig — continuation (2026-08-31)

## A. Corporate / IP status updates

| Fact | Detail |
|---|---|
| **High-Tech Enterprise** | Listed in Shenzhen 2024 HNTE batch 2 as **深圳旗鱼体育传播有限公司**, cert **GR202444208141** |
| Site IP boast | Still: **2 invention patents + 23 soft copyrights** (ZL201910975113.6, ZL201910989617.3) |
| Soft著 titles | Still **not public** without certificate numbers |
| 深圳旗鱼工业设计有限公司 | **Unrelated** (industrial design, 吴冬) — appeared on 2018 soft著 subsidy lists; do not merge |

## B. New software surface: **Sailfish-App** (`/sf-cloud-h5/`)

Uni-app H5 titled **「Sailfish-App」** / **旗鱼赛事管理**.

- Uni appId: `__UNI__BB85F3F`
- Stack: Vue + uni-app; auth via `/sf-admin/api/admin-api/`
- Deep-links to `/sf-admin` and `/sf-training`
- Live API responds (unauthenticated → `401 账号未登录`)

### App modules (from route + CJK strings)

| Area | Pages / features |
|---|---|
| Auth | `/pages/login`, `/pages/qy-login`, custom-login + refresh-token (`clientId=uniapp`), SMS/email SSO paths |
| Match ops | calendar, race, control, start-time / course / **全召轨迹**, check-in / checkout / check records / check WD |
| Devices | device list/detail/add, **风力设备**, **自动浮标**, club devices, device share history |
| Media | GoPro list + config (`pagesSub/gopro/*`) |
| Club | club device management |
| Infra | app version check: `GET …/infra/app-versions/getByAppId` |

### Auth API paths observed

```
/admin-api/system/auth/custom-login
/admin-api/system/auth/get-permission-info
/admin-api/system/auth/logout
/admin-api/system/auth/refresh-custom-token?clientId=uniapp&refreshToken=
/system/uc/sso/sms|email|password/login
/system/tenant/get-id-by-name
```

This confirms the **ops mobile client** for race control + hardware fleet (Tracer / Windwatcher / auto-buoy / GoPro), complementary to SF-Traj spectator UX.

## C. Infrastructure notes

| Host | Result |
|---|---|
| `www.sfcdn.cn` | nginx default page (CDN placeholder) |
| `base.saill.cn` / `:9505` | timeout / connection refused (legacy asset host still referenced in SPA) |
| `live.|traj.|api.|admin.`saill.cn | TLS hostname mismatch or 403 |
| `粤ICP备18008383号-3` historically on **sfcdn.cn** | Confirms Sailfish controlled that CDN domain |

## D. Patents — still 8 families / 12 pubs

No additional assignee hits found this pass. Wind patent **CN113588153A** full claims still blocked (Google Patents 503 + Chinese mirrors captcha/login). Title/product alignment to Windwatcher remains.

Soft著: HNTE status implies they filed enough IP for certification; **23 soft著 claim is plausible** but titles remain undisclosed.

## E. Suggested next digs (when unblocked)

1. Obtain soft著 certificate list (ask Sailfish / paid Qichacha IP tab).  
2. Capture authenticated Sailfish-App traffic (device + race-control endpoints).  
3. Re-fetch CN113588153A claims when GP available.  
4. Map SF-Traj public share URL query params from a live event.
