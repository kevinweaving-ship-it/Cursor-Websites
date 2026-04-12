#!/usr/bin/expect -f
# Deploy frontend index.html to live only. Same SSH credentials as deploy-api-live.sh.
# Run from project root: expect sailingsa/deploy/deploy-frontend-only.sh
# Or: ./sailingsa/deploy/deploy-frontend-only.sh (if executable)

set timeout 60
set password "TimAdd#072082"
set server "102.218.215.253"
set user "root"
set web_root "/var/www/sailingsa"

set script_dir [file dirname [info script]]
set project_root [file normalize "$script_dir/../.."]
set index_html "$project_root/sailingsa/frontend/index.html"

if {![file exists $index_html]} {
    puts "ERROR: index.html not found: $index_html"
    exit 1
}

puts "=========================================="
puts "SailingSA — Deploy frontend (index.html) only"
puts "=========================================="
puts "Server: ${user}@${server}"
puts "Target: ${web_root}/index.html"
puts ""

puts "Step 1: Copying index.html to ${web_root}/index.html ..."
spawn scp -o StrictHostKeyChecking=no $index_html ${user}@${server}:${web_root}/index.html
expect {
    "password:" { send "$password\r"; exp_continue }
    "100%" { expect eof }
    eof { }
    timeout { puts "ERROR: SCP timeout"; exit 1 }
}
wait
puts "  Done"
puts ""
puts "Deploy complete. Hard refresh browser (Cmd+Shift+R) to see changes."
puts ""
