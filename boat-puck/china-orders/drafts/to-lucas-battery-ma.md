# To Lucas — confirm our calc or send actual mA

Voltage now in: **3.3–6.5 V, typically 5 V**.

---

Got the 7 points, thank you.

Voltage **3.3–6.5 V (typically 5 V)** noted.

That 22 dB we take as **22 dBm** TX:

- 22 dBm = **158 mW** RF out
- LoRa radio only, while transmitting: typically **~100–130 mA on the 3.3 V rail**
- At **5 V** in (through a regulator) that is roughly **~80–100 mA** at the 5 V input — radio only
- GNSS / RTK on the WT-43 is **extra** and we have not counted it

Please **confirm** those currents for WT-43-BK-LORA and WT-43-RK-LORA, **or send the actual**:

- mA **transmitting** at 5 V
- mA **idle / receive** at 5 V
- with GNSS on, if you have it

Need that to size the battery.
