# Sent log — FOI pack (21 Nov 2026)

**From:** James Porter `<investigation@sailingsa.co.za>`  
**Sent via:** GoWifi MiaB SMTP (`box.gowifi.co.za:587`), authenticated  
**Bodies:** [`sent/bodies/`](sent/bodies/)  
**Reply watch:** timer `bruce-sunrise-mail-replies` every 12h; file under [`replies/`](replies/)

Do **not** use Kevin Weaving on these letters. Signatory is **James Porter**.

| # | Authority | To | Cc | Message-ID | Delivery (Postfix) | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | France — Var associations | `pref-associations@var.gouv.fr` | `sp-associations-draguignan@var.gouv.fr` | `<179522051001.1740393.13066934475540012954@sailingsa.co.za>` | **To:** accepted `250` at `fimad.interieur.gouv.fr` (queued `B43D4120049`). **Cc:** **bounced** `554 5.7.1 User Unknown` | Primary delivered; Draguignan CC dead — do not re-CC |
| 2 | Poland — REJA24 | `pomoc@reja24.gov.pl` | `w.stepien@pya.org.pl`, `s.sadowska@pya.org.pl` | `<179522051075.1740393.4699697048863342831@sailingsa.co.za>` | **To:** `250` at `poczta.reja24.gov.pl` (`2C79A220064`). **Both CCs:** `250` Outlook | Delivered |
| 3 | Greece — Lefkada Port Fund | `dltl@lefkada.gov.gr` | — | `<179522051086.1740393.13301618331633995159@sailingsa.co.za>` | `250` at `mx.otenet.gr` (`7DECB100071`) | Delivered |

Times: **21 Nov 2026 ~02:21–02:22 Africa/Johannesburg** (SAST on the box).

## Bounce filed

- NDR in INBOX: Cc `sp-associations-draguignan@var.gouv.fr` unknown. France **To** still accepted.
- **Re-check 21 Nov 2026 ~17:55 SAST:** live [var.gouv.fr démarches associations](https://www.var.gouv.fr/Demarches/Associations-Fondations-et-fonds-de-dotations/Association-loi-1901/Associations-loi-1901-et-demarches) still lists **only** `pref-associations@var.gouv.fr` for arrondissements Toulon **+ Draguignan + Brignoles** (DCL Toulon). The Draguignan sous-préfecture address is **obsolete** (old annuaires). **No resend** — correct mailbox already got the letter.

## Inbox checks

| When (Africa/Johannesburg) | INBOX | New authority replies |
| --- | --- | --- |
| 21 Nov 2026 ~02:22 | 1 (France Cc NDR only) | — |
| **21 Nov 2026 14:00** | still **1** — same NDR only | **none** from Var / REJA24 / Lefkada |
| **21 Nov 2026 15:56** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **22 Nov 2026 02:15** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **22 Nov 2026 14:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **23 Nov 2026 02:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **23 Nov 2026 14:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **24 Nov 2026 02:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **24 Nov 2026 14:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **25 Nov 2026 02:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **25 Nov 2026 14:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |
| **26 Nov 2026 02:00** | still **1** — same NDR; Spam empty | **none** from Var / REJA24 / Lefkada |

Timer continues every 12h (~5 days since send; MX still empty).

## DNS note (inbound)

Public dig (21 Nov 2026 after send): **MX for `sailingsa.co.za` empty** at Google/Cloudflare resolvers. Outbound worked (DKIM `d=sailingsa.co.za; s=mail` present on the France message). **Replies may not land** until MX `10 box.gowifi.co.za` (+ SPF/DKIM TXT as MiaB prints) is published at GoDaddy. Check mailbox anyway on each timer; fix MX if still missing.

## Portal (Poland)

Email alone may not issue `odpis pełny`. Still submit https://interesant.reja24.gov.pl form R24-OW when fee/payment path is available.
