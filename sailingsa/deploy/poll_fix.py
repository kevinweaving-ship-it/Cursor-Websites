#!/usr/bin/env python3
"""Fix polling to stop when event is complete or no active race."""

import sys

with open('/var/www/sailingsa/api/api.py', 'r') as f:
    content = f.read()

# Add shouldPoll helper function before the setInterval calls
old_marker = '  /* Keep open pages in sync without refresh (poll + BroadcastChannel push). */'
new_code = '''  /* Stop polling if event complete or no active race */
  function shouldPoll(){
    var pg=document.querySelector('.regatta-page[data-live-board-tint-rid]');
    if(!pg) return false;
    var dayDone=pg.getAttribute('data-live-day-done')==='1';
    var trackIdle=pg.getAttribute('data-live-track-idle')==='1';
    if(dayDone && trackIdle) return false;
    return true;
  }
  /* Keep open pages in sync without refresh (poll + BroadcastChannel push). */'''

if old_marker not in content:
    print("ERROR: Could not find marker for insertion point")
    sys.exit(1)

content = content.replace(old_marker, new_code)

# Update setInterval for refreshFromServer
old_interval1 = "setInterval(function(){ if (!document.hidden) refreshFromServer(); }, 8000);"
new_interval1 = "setInterval(function(){ if (!document.hidden && shouldPoll()) refreshFromServer(); }, 8000);"
content = content.replace(old_interval1, new_interval1)

# Update setInterval for refreshGunFromLiveRace
old_interval2 = "setInterval(function(){ if (!document.hidden) refreshGunFromLiveRace(); }, 5000);"
new_interval2 = "setInterval(function(){ if (!document.hidden && shouldPoll()) refreshGunFromLiveRace(); }, 5000);"
content = content.replace(old_interval2, new_interval2)

with open('/var/www/sailingsa/api/api.py', 'w') as f:
    f.write(content)

print("Done - polling fix applied")
