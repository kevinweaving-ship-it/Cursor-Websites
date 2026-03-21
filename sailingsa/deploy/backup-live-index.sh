#!/usr/bin/expect -f
# Pull live index.html to a timestamped backup. Same credentials as deploy-frontend-only.sh.
# Run from project root: expect sailingsa/deploy/backup-live-index.sh

set timeout 30
set password "TimAdd#072082"
set server "102.218.215.253"
set user "root"
set web_root "/var/www/sailingsa"

set script_dir [file dirname [info script]]
set project_root [file normalize "$script_dir/../.."]
set backup_name "index.html.live.BU_[clock format [clock seconds] -format %Y%m%d_%H%M%S]"
set backup_path "$project_root/sailingsa/frontend/$backup_name"

puts "=========================================="
puts "SailingSA — Backup live index.html"
puts "=========================================="
puts "Server: ${user}@${server}"
puts "Save to: $backup_path"
puts ""

spawn scp -o StrictHostKeyChecking=no ${user}@${server}:${web_root}/index.html $backup_path
expect {
    "password:" { send "$password\r"; exp_continue }
    "100%" { expect eof }
    eof { }
    timeout { puts "ERROR: SCP timeout"; exit 1 }
}
wait
puts "Done."
exit 0
