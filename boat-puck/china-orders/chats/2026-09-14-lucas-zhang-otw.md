# Lucas Zhang — OTW / Anzewei (WhatsApp)

**Supplier:** Shenzhen Anzewei / On The Way (`ontheway-tech.com`)  
**Thread:** 2026-09-14 → 2026-09-15  
**Status:** Quoted. **Do not PI yet** (Moko/Dragino first). Range + Sailfish **sent**. TX power **22 dBm**; other six Qs waiting. Battery **mA** still open.

Sent text: [`../drafts/to-lucas-range-and-sailfish.md`](../drafts/to-lucas-range-and-sailfish.md)

---

## Extract

| When | What |
|------|------|
| 14 Sep 14:48 | Lucas: WT-43-RK-LORA ×2, WT-43-BK-LORA ×1, assume 868 MHz |
| 14 Sep 14:57 | Sample prices: RK **$40**, BK **$55** |
| 14 Sep 15:16 | Kevin: **3× RK** + **1× BK** |
| 14 Sep 16:03 | Shenzhen address to 吴建军 / Eric |
| 14 Sep 19:01 | Lucas: will draft order tomorrow; asked application |
| 14 Sep 19:02–19:13 | Kevin: SA boat racing, Multitrack / SailingSA, automated regatta, 1 cm starts, LoRa + 4G base, courses ~3 km (some 8–10 km) |
| 15 Sep 04:20 | Lucas: how will you pay? |
| 15 Sep 10:31 | Kevin: team still on spec; also asked Minew nRF54L15 DK (not OTW) |
| 15 Sep 11:11 | Kevin: **wait** — combine with Eric shipment, not urgent today |
| 15 Sep 11:36 | Lucas last Q: **RTK communication range?** |
| 15 Sep 11:46 | Kevin: committee↔pin 100–150 m; 1 cm at start only; pucks on marks/finish |
| 15 Sep (sent) | Kevin: range + 旗鱼/saill.cn — not cloning Sailfish; RTK for start line; LoRa = corrections only; 7 spec Qs; **do not order yet** |
| 15 Sep 12:20 | Lucas: will reply to the seven questions later |
| 15 Sep 12:27–13:04 | LoRa power: Kevin asked consumption for battery sizing; Lucas said **22 dB** (treat as **22 dBm TX power**, not mA draw) |

---

## Transcript

[2026/09/14, 14:48:21] ~Lucas Zhang: Nice to meet you. I'm Lucas.
[2026/09/14, 14:48:29] ~Lucas Zhang: •⁠  ⁠WT-43-RK-LORA × 2
•⁠  ⁠WT-43-BK-LORA × 1
[2026/09/14, 14:48:31] Kevin Weaving: same here Lucas
[2026/09/14, 14:48:35] ~Lucas Zhang: Assume the 868mhz models
[2026/09/14, 14:48:41] Kevin Weaving: Yes please
[2026/09/14, 14:48:50] ~Lucas Zhang: No problem. We can provide...
[2026/09/14, 14:49:13] Kevin Weaving: We have an office in Shenzhen where samples can be shipped to ... they will ship to us
[2026/09/14, 14:49:51] ~Lucas Zhang: Sure, you can send me your address in Shenzhen.
[2026/09/14, 14:50:45] Kevin Weaving: Will do ...
[2026/09/14, 14:51:20] Kevin Weaving: You have URL/Website page for the 868Mhz versions ?
[2026/09/14, 14:52:13] Kevin Weaving: and sample prices
[2026/09/14, 14:52:43] ~Lucas Zhang: For the current Lora we have, we can change the frequency to 433 MHz, and we can also change it to 868 MHz for the Lora module.
[2026/09/14, 14:54:05] ~Lucas Zhang: I had a Vietnamese friend before who also needed 868Mhz. After testing it, he was extremely satisfied.😄
[2026/09/14, 14:54:07] Kevin Weaving: Ok, .... good
[2026/09/14, 14:57:25] ~Lucas Zhang: •⁠  ⁠WT-43-RK-LORA  40USD/pcs
•⁠  ⁠WT-43-BK-LORA  55USD/PCS
[2026/09/14, 15:04:09] Kevin Weaving: Great ..
[2026/09/14, 15:04:26] Kevin Weaving: I will pass onto buyers shortly and revert with address
[2026/09/14, 15:16:51] Kevin Weaving: 3pcs  ⁠WT-43-RK-LORA  40USD/pcs
1pc ⁠WT-43-BK-LORA  55USD/PCS
[2026/09/14, 16:03:44] Kevin Weaving: Address 

深圳市福田区华强北友谊路上步工业区404栋2楼212号吴建军18680660780 kevin
[2026/09/14, 19:01:07] ~Lucas Zhang: ok
[2026/09/14, 19:01:33] ~Lucas Zhang: I will draft the order for you tomorrow.
[2026/09/14, 19:01:55] ~Lucas Zhang: Can you tell me about your application scenario?
[2026/09/14, 19:02:41] Kevin Weaving: Sure 

We involved with Boat racing in South Africa 

We are gps tracking based company 

Multitrack.co.za
[2026/09/14, 19:03:00] Kevin Weaving: We also host sailingsa.co.za
[2026/09/14, 19:03:54] Kevin Weaving: We have been asked to developing a racing / regatta for boats competing that is fully automated 

System needs 1cm accuracy for starts > which boats over the line
[2026/09/14, 19:04:26] Kevin Weaving: And also track boats around the court and rouding marks around the course
[2026/09/14, 19:04:59] Kevin Weaving: We often have international events locally
[2026/09/14, 19:07:12] Kevin Weaving: Next year March 27 windsurfer Worlds been held here > 200+ competitors
[2026/09/14, 19:08:00] ~Lucas Zhang: How long is the race distance approximately in kilometers?
[2026/09/14, 19:08:06] Kevin Weaving: We plan to use Lora as offline network with a base with 4G backhaul
[2026/09/14, 19:10:00] Kevin Weaving: Most are a couse and from start to furtherist mark mostly under 3km 

Other classes can be up to 8-10km

In that case we would have Lora extra gateways with 4G backhalls in between so no boat more than 3-4km to a gateway
[2026/09/14, 19:10:34] Kevin Weaving: They have offshore races 50-60km but that uses different system and starlinks onboard
[2026/09/14, 19:11:07] Kevin Weaving: So our boat puck can still work BLE to connect to backhaul
[2026/09/14, 19:13:25] Kevin Weaving: There are other system in the market but very expensive and limited in what they can do … we trying to build a better system cheaper > more reliable and more features
[2026/09/15, 04:00:08] ~Lucas Zhang: got it
[2026/09/15, 04:00:37] ~Lucas Zhang: Sorry, I was too late yesterday. I was resting at that time.
[2026/09/15, 04:20:58] ~Lucas Zhang: How can you make the payment?
[2026/09/15, 10:30:44] ~Lucas Zhang: Hi
[2026/09/15, 10:30:58] Kevin Weaving: Morning
[2026/09/15, 10:31:37] Kevin Weaving: Development team still looking into specification and also asked for a Dev Board
[2026/09/15, 10:31:53] Kevin Weaving: https://store.minewsemi.com/product/nrf54l15-me54bs62-bluetooth-module-me54be62-development-kit/
[2026/09/15, 10:37:19] ~Lucas Zhang: Is this a Bluetooth module?
[2026/09/15, 10:37:49] ~Lucas Zhang: No problem. Could you please tell me what the current disputes are? I can help you solve some of them first.
[2026/09/15, 10:38:00] Kevin Weaving: Yes, they busy with final list from your site
[2026/09/15, 10:38:23] Kevin Weaving: once I have it I will let you have final order … list for PI
[2026/09/15, 10:41:43] ~Lucas Zhang: Understood. The products you need to purchase come in different types, and our RTK module is one of them, right?
[2026/09/15, 11:05:04] ~Lucas Zhang: Do we need to place the order right now?
[2026/09/15, 11:11:09] Kevin Weaving: No, Wait please for our team to give their list as have time to ship to Eric as many other orders been combined by him before shipping to us (Not that urgent that needs to be done today)
[2026/09/15, 11:25:18] ~Lucas Zhang: ok，got it
[2026/09/15, 11:25:46] ~Lucas Zhang: When is the next competition scheduled to take place?
[2026/09/15, 11:27:34] Kevin Weaving: Their are some happening every weekend almost ... for clubs (smaller ones) 

next nationals 420 is about 2 weeks time 25 boats 

But bigger one is decemeber 150 boats
[2026/09/15, 11:36:43] ~Lucas Zhang: Regarding our LORA RTK module, have you ever considered the issue of RTK communication range?
[2026/09/15, 11:46:08] Kevin Weaving: Yes, The master (committee) boat and the start Pin are about max 100-150m apart and the boats (Pucks) are on the line between them on the start where 1cm accuracy required (only start) and Base is on Main boat (controls the races)
[2026/09/15, 11:46:34] Kevin Weaving: and each mark rounded and finish pin / boat also will have a std puck installed
[2026/09/15, 11:48:43] Kevin Weaving: es, communication range is important. Our application is sailing race management on open water. The RTK base will normally be on the committee boat or shore, and the fleet could extend approximately 2–5 km from the base with clear line of sight over water.

We need reliable RTCM correction transmission from one WT-43-BK-LORA base to all WT-43-RK-LORA rover units simultaneously. Please confirm the actual tested LoRa range over open water, LoRa frequency/band, transmit power, antenna specification, data rate, and maximum number of rover units that one base can support. We may have 100+ boats.

Please also confirm whether the base broadcasts RTCM continuously so all rover units receive the same corrections without individual connections.

[2026/09/15] Kevin Weaving: *(sent — range + Sailfish; supersedes the 11:48 draft above)*

Yes — range is one of the first things we looked at.

The critical part is the start. Committee boat and start pin are only about 100–150 m apart. Boats sit on that line. That is the only place we need ~1 cm. Around the course, tracking does not need centimetre accuracy.

On a typical race the fleet is about 2–5 km from the committee boat, open water, line of sight. Marks and finish also have a tracker.

We already know the GPS tracking systems used in China. The one in your market is Sailfish / 旗鱼体育:

https://www.saill.cn/

They supply the national trajectory system for Chinese sailing — 中帆协 events and National Games / 全运会. Each boat gets a GPS unit (the orange box). Organising committees and the association fund it (teams often pay a per-boat trajectory fee; the rest is covered by the event). It does live tracks, safety, replay, video overlay, and protest support. That is a government / association tracking and media platform. It works well for that job.

We are not building another Sailfish.

Their system is normal GPS — good enough for “where is the fleet” and replay. It is not accurate enough to automatically call who was over the start line. That call is often decided in a few tens of centimetres. Phone GPS / orange-box GPS cannot do that. That is why we are using RTK, not another GPS tracking website.

LoRa is only so the RTK corrections can reach the boats on the water without depending on cellular for every unit.

Please confirm on WT-43-BK-LORA → WT-43-RK-LORA:

Tested LoRa range over open water
868 MHz band / frequency
Transmit power
Antenna
Data rate
How many rover units one base can serve at once
Does the base broadcast RTCM continuously to all rovers (same corrections, no one-to-one connection)?
Still waiting for our team’s final sample list. Please do not place the order yet.

[2026/09/15, 12:06:34] Kevin Weaving: ‎Read more
[2026/09/15, 12:20:56] ~Lucas Zhang: OK. I will reply to you regarding the seven questions you raised later.
[2026/09/15, 12:27:56] ~Lucas Zhang: Regarding the power requirements for LORA
[2026/09/15, 12:29:54] Kevin Weaving: Yes …?
[2026/09/15, 12:33:16] ~Lucas Zhang: How much power does the LoRa module need?
[2026/09/15, 12:34:27] Kevin Weaving: That means what would its power consumption be > when transmitting so can size battery for system
[2026/09/15, 12:35:26] ~Lucas Zhang: yes
[2026/09/15, 12:37:07] Kevin Weaving: I.E> What power does you device require
[2026/09/15, 13:04:34] ~Lucas Zhang: 22db
[2026/09/15, 13:04:40] Kevin Weaving: Ok
