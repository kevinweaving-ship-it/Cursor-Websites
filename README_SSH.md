# LIVE SERVER SSH ACCESS

## Server IP
102.218.215.253

## SSH User
root

## Connect Command
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253
```
Or with password: `ssh root@102.218.215.253`

## If blocked by fail2ban
```bash
sudo fail2ban-client status
sudo fail2ban-client unbanip <your_ip>
```

## Restart App
```bash
sudo systemctl restart sailingsa-api
```

## Check Logs
```bash
sudo journalctl -u sailingsa-api -f
```

## Check Gunicorn / Uvicorn
Live runs **uvicorn** (not gunicorn). Check process count:
```bash
ps aux | grep uvicorn
```
Service file: `/etc/systemd/system/sailingsa-api.service`

**Primary deploy/SSH reference:** `sailingsa/deploy/SSH_LIVE.md`
