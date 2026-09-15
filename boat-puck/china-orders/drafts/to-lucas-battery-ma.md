# To Lucas — that 22 dB vs battery

**22 dB = 22 dBm RF out, not battery.**  
22 dBm = **158 mW** leaving the antenna. Typical LoRa PA at 22 dBm is ~100–130 mA @ 3.3 V **for the radio only** (SX1262 class). That does **not** include GNSS/RTK on the WT-43. Cannot size the puck pack from 22 dBm.

---

That transmit power (22 dB) we understand.

What battery power it consume is the question — mA while transmitting and idle, and the supply voltage. Need that to size the battery.
