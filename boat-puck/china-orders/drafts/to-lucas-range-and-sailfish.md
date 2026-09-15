# To Lucas — range + Sailfish (not sent)

Reply to: *Regarding our LORA RTK module, have you ever considered the issue of RTK communication range?*

Do **not** add puck/gateway/BLE/Starlink roadmap.

---

Yes — range is one of the first things we looked at.

The critical part is the **start**. Committee boat and start pin are only about **100–150 m** apart. Boats sit on that line. That is the only place we need **~1 cm**. Around the course, tracking does not need centimetre accuracy.

On a typical race the fleet is about **2–5 km** from the committee boat, open water, line of sight. Marks and finish also have a tracker.

We already know the GPS tracking systems used in China. The one in your market is **Sailfish / 旗鱼体育**:

https://www.saill.cn/

They supply the national trajectory system for Chinese sailing — **中帆协** events and **National Games / 全运会**. Each boat gets a GPS unit (the orange box). Organising committees and the association fund it (teams often pay a per-boat trajectory fee; the rest is covered by the event). It does live tracks, safety, replay, video overlay, and protest support. That is a government / association tracking and media platform. It works well for that job.

We are **not** building another Sailfish.

Their system is **normal GPS** — good enough for “where is the fleet” and replay. It is **not** accurate enough to automatically call who was over the start line. That call is often decided in a few tens of centimetres. Phone GPS / orange-box GPS cannot do that. That is why we are using **RTK**, not another GPS tracking website.

LoRa is only so the **RTK corrections** can reach the boats on the water without depending on cellular for every unit.

Please confirm on **WT-43-BK-LORA → WT-43-RK-LORA**:

1. Tested LoRa range over open water
2. 868 MHz band / frequency
3. Transmit power
4. Antenna
5. Data rate
6. How many rover units one base can serve at once
7. Does the base **broadcast RTCM continuously** to all rovers (same corrections, no one-to-one connection)?

Still waiting for our team’s final sample list. Please do **not** place the order yet.
