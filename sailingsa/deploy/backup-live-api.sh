#!/usr/bin/expect -f
# Pull live api.py to a timestamped backup.
set timeout 30
set password "TimAdd#072082"
set server "102.218.215.253"
set user "root"
set api_dir "/var/www/sailingsa/api"

set script_dir [file dirname [info script]]
set project_root [file normalize "$script_dir/../.."]
set backup_name "api.py.live.BU_[clock format [clock seconds] -format %Y%m%d_%H%M%S]"
set backup_path "$project_root/$backup_name"

puts "Backup live api.py -> $backup_path"
spawn scp -o StrictHostKeyChecking=no ${user}@${server}:${api_dir}/api.py $backup_path
expect {
    "password:" { send "$password\r"; exp_continue }
    "100%" { expect eof }
    eof { }
    timeout { puts "ERROR: timeout"; exit 1 }
}
wait
puts "Done."
exit 0
