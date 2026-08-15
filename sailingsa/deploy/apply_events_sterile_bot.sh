#!/usr/bin/expect -f
set timeout 120
spawn scp -o StrictHostKeyChecking=no /workspace/sailingsa/deploy/patch_events_sterile_bot.py root@102.218.215.253:/tmp/patch_events_sterile_bot.py
expect {
  -re "(?i)password:" { send "TimAdd#072082\r"; exp_continue }
  eof {}
}
spawn ssh -o StrictHostKeyChecking=no root@102.218.215.253 python3 /tmp/patch_events_sterile_bot.py
expect {
  -re "(?i)password:" { send "TimAdd#072082\r"; exp_continue }
  eof {}
}
catch {wait}
spawn ssh -o StrictHostKeyChecking=no root@102.218.215.253 bash /tmp/apply_quarantine_events.sh
expect {
  -re "(?i)password:" { send "TimAdd#072082\r"; exp_continue }
  eof {}
}
catch {wait}
