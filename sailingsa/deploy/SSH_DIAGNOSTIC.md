# SSH Diagnostic — Isolate Layer by Layer

**Target:** `102.218.215.253` port 22

---

## 1. Test on Mac Terminal (WiFi)

```bash
nc -vz 102.218.215.253 22
```

| Output | Meaning |
|--------|---------|
| `succeeded!` | Port open → SSH should work |
| `timed out` | Server firewall still blocking |
| `No route to host` | Local/router/ISP or **Dream Machine blocking outbound 22** |
| `Connection refused` | sshd not listening on server |

---

## 2. Router Test (Dream Machine suspicion)

If WiFi gives `No route to host`:

1. Connect Mac to **mobile hotspot** (USB or WiFi)
2. Turn OFF WiFi
3. Run:

```bash
nc -vz 102.218.215.253 22
```

- **Succeeds on hotspot, fails on WiFi** → Dream Machine blocking outbound SSH

---

## Layers to isolate

- VPS firewall (fail2ban)
- ISP routing
- UDM (Dream Machine) firewall
- Local Mac firewall
