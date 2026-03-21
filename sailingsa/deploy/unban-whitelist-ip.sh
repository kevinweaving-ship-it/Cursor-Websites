#!/bin/bash
# Run ON SERVER via hosting console (web SSH). Unban + whitelist 165.165.115.95

# Unban the WiFi IP
fail2ban-client set sshd unbanip 165.165.115.95

# Ensure jail.local exists
touch /etc/fail2ban/jail.local

# Write clean config
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 165.165.115.95

[sshd]
enabled = true
maxretry = 8
findtime = 10m
bantime = 30m
EOF

# Restart fail2ban
systemctl restart fail2ban

# Confirm
fail2ban-client status sshd
