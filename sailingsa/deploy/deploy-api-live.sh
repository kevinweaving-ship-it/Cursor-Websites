#!/usr/bin/expect -f
# Force live API deploy only. Same SSH credentials as push-to-cloud-expect.exp.
# Run from project root: expect sailingsa/deploy/deploy-api-live.sh
# Or: ./sailingsa/deploy/deploy-api-live.sh (if executable)

set timeout 60
set password "TimAdd#072082"
set server "102.218.215.253"
set user "root"
set api_dir "/var/www/sailingsa/api"

set script_dir [file dirname [info script]]
set project_root [file normalize "$script_dir/../.."]
set api_py "$project_root/api.py"

if {![file exists $api_py]} {
    puts "ERROR: api.py not found: $api_py"
    exit 1
}

puts "=========================================="
puts "SailingSA — Deploy API to live only"
puts "=========================================="
puts "Server: ${user}@${server}"
puts "Target: ${api_dir}/api.py"
puts ""

# 1) SCP api.py
puts "Step 1: Copying api.py to ${api_dir}/api.py ..."
spawn scp -o StrictHostKeyChecking=no $api_py ${user}@${server}:${api_dir}/api.py
expect {
    "password:" { send "$password\r"; exp_continue }
    "100%" { expect eof }
    eof { }
    timeout { puts "ERROR: SCP timeout"; exit 1 }
}
wait
puts "  Done"
puts ""

# 2) Restart sailingsa-api
puts "Step 2: Restarting sailingsa-api..."
spawn ssh -o StrictHostKeyChecking=no ${user}@${server} "sudo systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
expect {
    "password:" { send "$password\r"; exp_continue }
    "active" { }
    eof { }
    timeout { puts "ERROR: SSH restart timeout"; exit 1 }
}
wait
puts "  Done"
puts ""

# 3) Verify: curl regatta URL (run locally)
puts "Step 3: Verify live (first 120 lines)..."
puts "----------------------------------------"
spawn sh -c "curl -s https://sailingsa.co.za/regatta/2025-sa-youth-nationals-dec-2025 | head -n 120"
expect eof
wait
puts "----------------------------------------"
puts ""

# 4) journalctl on server
puts "Step 4: journalctl -u sailingsa-api -n 50 --no-pager"
puts "----------------------------------------"
spawn ssh -o StrictHostKeyChecking=no ${user}@${server} "journalctl -u sailingsa-api -n 50 --no-pager"
expect {
    "password:" { send "$password\r"; exp_continue }
    eof { }
    timeout { puts "ERROR: journalctl timeout"; exit 1 }
}
wait
puts "----------------------------------------"
puts ""
puts "Deploy complete. Check above for <h2>Classes</h2>, <h2>Top Results</h2>, and no 500s in journal."
puts ""
