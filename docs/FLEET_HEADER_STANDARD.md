# Fleet header standard (results URLs)

Standard fleet card on every Event / results URL, matching Western Cape Dinghy Championships **420 Fleet**:

| Slot | Content |
| --- | --- |
| **Left** | Class / fleet logo (class catalogue artwork) |
| **Centre** | `{Class} Fleet` (text). Scoring never belongs here. |
| **Right** | Host club logo |

Sailed line under the title stays: `Sailed: N, Discards: N, To count: N, … Scoring system: …`

## Class == fleet

When the block is a single class (class name and fleet name are the same after stripping a trailing `Fleet`), use the standard above. Keep the stored `fleet_label` casing (`ILCA 6 Fleet`, not a catalogue rewrite).

Examples: `420 Fleet`, `Hunter 19 Fleet`, `ILCA 6 Fleet`.

## Class != fleet — leave as is

Do **not** rename or invent a class logo when the fleet is mixed or the fleet name is not the class name.

Examples: `Open A Fleet`, `Hobie Fleet` (class is Hobie 16), `Keelboat Fleet` (L26 / Beneteau / Sadler). Keep the stored `fleet_label`. Still strip scoring text from the title.

## Never put scoring in a fleet title

`block_label_raw`, `fleet_label`, and the on-page title must **not** include scoring or rating:

- Forbidden: `Hobie Fleet — ToT - Custom`, `Hunter 19 Fleet — ToT - Custom Fleet`, `… Appendix A Fleet`
- Scoring system (`ToT - Custom`, `Appendix A`, …) lives on the **sailed line only**
- `block_label_raw` should match the fleet name (`Hobie Fleet`), not `{fleet} — {scoring}`

Live title builder: `_strip_scoring_system_from_fleet_title` in `/var/www/sailingsa/api/api.py`.

## Exceptions (do not “fix”)

- **Lipton**: Event logo left, class logo right (not host on the right of the fleet card).
- **Cape Classic 2026 ZVY**: existing logo + word `Fleet` title rule stays.
- **MAC / TSC endurance**: keep specialised block titles (Line Honours, Handicap, etc.).
