# Dev WhatsApp Chat

Source dump **2026-09-15**. China-order / Google Sheet: [`../ORDERS.md`](../ORDERS.md) + [`../sheet.csv`](../sheet.csv).

Richard thread (qty + vineyard): [`2026-09-10-richard-frost.md`](2026-09-10-richard-frost.md).

---

## 2026-09-15 — order list (as given)

```
Moko
LW014 - Wearable watch
LW013 - Smart button


Dragion

For the farming 
WSC2-L LoRaWAN Weather Station Kit
SE0X-xB/xS Soil Moisture & EC Transmitter
SPH01-xB/xS Soil pH Sensor
S31_S31B-xB/xS Temperature & Humidity Sensor
LT-22222-L Offices, industrial buildings LoRaWAN I/O Controller

For the develop
LA66 LoRaWAN Module


And then 4 x LW006 - Smart badges
```

### Locked for PI

| Supplier | SKU | Qty | Why |
|----------|-----|----:|-----|
| Moko | LW014 EU868 (wrist / wearable) | **20** | Richard 10 Sep: “Let’s say 20?” + LW014 URL |
| Moko | LW013 EU868 smart button | **1** | Dev list; no qty → sample |
| Moko | LW006 EU868 smart badge | **4** | Dev: “4 x LW006” |
| Dragino | WSC2-L weather station kit EU868 | **1** | Farming |
| Dragino | SE01-LB EU868 (soil moisture & EC; SE0X if current) | **1** | Richard: SE01 / SE OX |
| Dragino | SPH01-LB EU868 soil pH | **1** | Farming |
| Dragino | S31B-LB EU868 (vineyard humidity) | **1** | Richard wants vineyard RH; **not** S31-CB (that page is NB-IoT) |
| Dragino | LT-22222-L EU868 I/O | **1** | Valve open/closed |
| Dragino | LA66 EU868 module | **1** | Dev |

**Not on PI:** LW010-CT (Kevin showed as cheaper alt only).
