"""Notes: hide Meta/Alibaba/AWS/Google crawler IPs from traffic Guest/Done lists.

Live applied 2026-08-15 via sailingsa/deploy/patch_crawler_cloud_hide.py

What changed on live api.py:
- _lean_is_google_crawler_ip / _lean_is_google_crawler_ua / _lean_is_crawler_cloud_ip
- Offline Done: crawler-cloud IPs forced into bots (no engagement pardon)
- Live: hard bot for those ranges (removed soft pass that let AWS Chrome UAs through as Guest)
- Cloud nets: added 44.0.0.0/8 and 50.16.0.0/14 (AWS EC2); Alibaba already in 47.74–47.96; Meta via FB prefixes

UI: Guests stay in Done/offline; bots remain under collapsed "Bots done / quarantined".

Does not re-enable presence recording.
"""
