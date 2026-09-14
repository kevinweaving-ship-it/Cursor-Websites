# SoftSIM module — China factory / direct buy (fits puck)

**Fit lock:** leftover strip ~**28.8 mm** beside WT-43 → module ≤ **24×24×2.4** (or EG915U **23.6×19.9**).  
**Qty when buying:** **×3** (same puck roles).  
**Not this sample PO yet** — enquiry when ready; SoftSIM **firmware** must be ordered explicitly (stock A7672 ≠ SoftSIM FW).

---

## Buy #1 (preferred) — SIMCom A7672 SoftSIM

| | |
|--|--|
| **Part** | **A7672E-LASE** (LTE only) or **A7672E-FASE** (LTE+BT+GNSS — GNSS unused; skip if costlier) |
| **Size** | **24 × 24 × 2.4 mm** — **fits** |
| **SoftSIM** | Yes — **Onomondo** or **Monogoto** SoftSIM **firmware** (ask factory for SoftSIM PN, not blank module) |
| **Bands (E)** | LTE B1/3/5/7/8/20/28 — OK for SA roaming IoT SIMs |
| **Factory** | **SIMCom** (Shanghai / Shenzhen sales) |
| **Product URL** | https://www.simcom.com/product/A7672X.html |
| **SoftSIM info** | https://onomondo.com/product/softsim-for-simcom/ |
| **Contact** | +86 21 31575100 · sales via https://www.simcom.com/ (Contact Us) |

### China distributors (module $ — SoftSIM FW = ask)

| Who | URL | Listed $ (module only) | Notes |
|-----|-----|------------------------|-------|
| **Misuxin Shenzhen** (A7672E-LASE) | https://misuxinelectronics.com/showpro_2816381_569.html | **~$17.32** (1+) → ~**$13.86** (1k+) | Email `info@misuxin.com` · +86-18826577755 · ask SoftSIM FW |
| **Misuxin** (A7672E-FASE) | https://misuxinelectronics.com/showpro_2816453_569.html | **~$21.94** (1+) → ~**$17.55** (1k+) | Same — SoftSIM PN required |
| **Alibaba board seller** (core board, not bare) | https://www.alibaba.com/product-detail/SIMCOM-A7672E-LASE-A7672E-FASE-A7672SA_1601121567806.html | ~**SG$19–22** board | **Too big for housing** — lab only |

**Sample kit cost (3× bare LASE @ ~$17):** ~**$51** + SoftSIM profile fees (Onomondo/Monogoto) + carrier PCB + FPC ant (~extra $5–15/ea design).

**Ask SIMCom / Misuxin (copy):**
```
Need A7672E SoftSIM (Onomondo or Monogoto FW) ×3 samples.
Confirm SoftSIM firmware PN (not physical SIM tray).
Ship to Eric Shenzhen. Quote USD + lead time.
```

---

## Buy #2 — Quectel EG915U SoftSIM (QuecOpen)

| | |
|--|--|
| **Part** | **EG915U-EU** (or GL/LA — pick SA/roaming bands) |
| **Size** | **23.6 × 19.9 × 2.4 mm** — **fits easier** |
| **SoftSIM** | Onomondo via **QuecOpen SDK** (build SoftSIM into FW) |
| **Factory** | **Quectel** Shanghai |
| **Product URL** | https://www.quectel.com/product/lte-cat-1-bis-eg915u-series/ |
| **SoftSIM** | https://onomondo.com/product/softsim-for-quectel/ |
| **Sales** | sales@quectel.com · +86 21 5108 6236 |

### China Alibaba class (module $ — SoftSIM = SDK work)

| Listing class | URL | Listed €/$ | Notes |
|---------------|-----|------------|-------|
| EG915U showroom | https://m.alibaba.com/showroom/eg915u-quectel.html | **~$11–17** / **€10–17** · MOQ 5–10 | Ask SoftSIM / QuecOpen capable lot |
| EG912U-GL (alt SoftSIM QuecOpen) | https://www.alibaba.com/product-detail/Brand-New-and-Original-Quectel-EG912U_1601366357056.html | **~$11–13** | **29×25** — **tight / no** in 28.8 strip |

**3× EG915U @ ~$12:** ~**$36** + QuecOpen SoftSIM eng time (more work than A7672 SoftSIM FW).

---

## Cost snapshot (3 pucks)

| Path | Module ×3 | SoftSIM path | Fit | Effort |
|------|----------:|--------------|-----|--------|
| **A7672E SoftSIM FW** | **~$52–66** | Flash SoftSIM profile | Best proven SoftSIM | Ask FW PN |
| **EG915U + QuecOpen SoftSIM** | **~$36–51** | Build SoftSIM in SDK | Slightly smaller | More eng |
| Dev board / EVB | $60–80+ | — | **No** | Lab only |

**Connectivity $ (ongoing):** Onomondo / Monogoto SoftSIM plan — separate from module; typically few $/mo per device (confirm when ordering profiles).

---

## Recommendation

1. **Enquiry first:** SIMCom / Misuxin — **A7672E SoftSIM FW ×3** → Eric.  
2. **Alt:** Quectel **EG915U-EU SoftSIM** if A7672 SoftSIM PN unavailable.  
3. Do **not** buy random A7672 without SoftSIM firmware line.  
4. Do **not** buy Alibaba “core board” for the puck.
