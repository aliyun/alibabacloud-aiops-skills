# Troubleshooting Guide

## Ping Failure Troubleshooting Flow

If Ping test fails, follow these steps:

### Step 1: Check Server-side Tunnel Status
```bash
sudo swanctl --list-sas
```
- If no SAs listed: Verify charon is running (`ps aux | grep charon`), check VICI socket exists (`ls -la /var/run/charon.vici`), then load connections (`swanctl --load-all`)
- If SAs show `ESTABLISHED` but no communication: Check routing and traffic statistics
```

### Step 2: Check Firewall Rules
Ensure UDP ports 500, 4500 and ESP protocol is allowed.

### Step 3: Verify PSK Match
```bash
sudo cat /etc/swanctl/swanctl.conf | grep -A2 "secrets"
```
Or view the secrets section in swanctl.conf and compare against Alibaba Cloud side configured PSK.

### Step 4: Check Configuration Parameter Consistency
- **IKE Version**: Both must be `ikev2`
- **Encryption Algorithm**: Both must match (e.g., `aes256`)
- **Authentication Algorithm**: Both must match (e.g., `sha256`)
- **DH Group**: Both must match (e.g., `group14` / `modp2048`)
- **LocalId/RemoteId**: Must match peer's public IP

> **Note**: For better security, use `aes256`, `sha256`, and `group14` (modp2048) if supported by both ends.

### Step 5: Check NAT Traversal Configuration
- If server behind NAT (only has private IP), ensure you've configured `encap=yes` in swanctl.conf
- Ensure using `local_addrs=%defaultroute` instead of specific internal IP

### Step 6: Check Routing Table Configuration
- Confirm Aliyun VPC route table has `{REMOTE_SUBNET} → VPN Gateway` route
- Confirm server-side has return route to Aliyun (usually default route)

### Step 7: View Traffic Statistics
```bash
sudo swanctl --list-sas --raw | grep -E "(bytes|packets)"
```
- If inbound/outbound traffic present: tunnel working normally, issue may be routing or firewall
- If no traffic: tunnel not fully established, check logs

### Step 8: Check Dual-tunnel Priority Configuration

When both IPsec tunnels show `ESTABLISHED` state but traffic is not flowing correctly, check the priority configuration.

**Detection Method:**
```bash
watch -n 2 'cat /proc/net/xfrm_stat | grep XfrmInTmplMismatch'
```
If `XfrmInTmplMismatch` continues growing, there may be routing conflicts.

**VICI/swanctl Solution:**
Ensure different `priority` values configured for both tunnels in `/etc/swanctl/swanctl.conf`:
- Primary tunnel `aliyun-vpn-master-child`: `priority = 100` (higher priority)
- Backup tunnel `aliyun-vpn-slave-child`: `priority = 200` (lower priority)

With priority-based routing:
- Both tunnels can be UP simultaneously
- Traffic prefers the tunnel with lower priority number (higher priority)
- If master tunnel fails, traffic automatically flows through slave tunnel

After configuring `priority`, reload configuration:
```bash
sudo swanctl --load-all
```

---

## Alibaba Cloud Side Log Viewing

For dual-tunnel mode, must specify each tunnel's TunnelId separately:

```bash
# Get both tunnel IDs
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VCO_ID} \
  --cli-query 'VpnConnections.VpnConnection[].TunnelOptionsSpecification.TunnelOptions[].{TunnelId:TunnelId, Role:Role}' \
  --user-agent AlibabaCloud-Agent-Skills

# Query primary tunnel logs
aliyun vpc describe-vpn-connection-logs \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VCO_ID} \
  --tunnel-id {TUNNEL_ID_MASTER} \
  --minute-period 60 \
  --user-agent AlibabaCloud-Agent-Skills

# Query backup tunnel logs
aliyun vpc describe-vpn-connection-logs \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VCO_ID} \
  --tunnel-id {TUNNEL_ID_SLAVE} \
  --minute-period 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Server-side Log Viewing

```bash
sudo journalctl -u strongswan-starter -u strongswan -u charon --since '10 minutes ago' --no-pager
```

Or view charon logs directly:
```bash
sudo swanctl --log
```

**Common Errors and Solutions:**
- `authentication failed`: PSK mismatch, check secrets section in `/etc/swanctl/swanctl.conf`
- `no suitable proposal found`: IKE/IPsec parameter mismatch, compare end-to-end configs
- `certificate validation failed`: Certificate issue, use PSK mode instead
- `unable to install source route`: Routing issue, check kernel param `net.ipv4.ip_forward`
- `vici connect failed`: VICI socket not found, ensure charon is running with vici plugin loaded

---

## VICI/swanctl Specific Issues

### Issue: "connecting to 'unix:///var/run/charon.vici' failed"

**Cause:** Charon daemon not running or VICI plugin not loaded.

**Solution:**
```bash
# Check if charon is running
ps aux | grep charon

# Start charon manually if needed
sudo /usr/lib/ipsec/charon &

# Verify vici plugin is loaded in /etc/strongswan.conf
# load = ... vici
```

### Issue: "configuration load failed"

**Cause:** Syntax error in swanctl.conf.

**Solution:**
```bash
# Check configuration syntax
sudo swanctl --load-all --debug

# Common syntax issues:
# - Missing quotes around strings with special characters
# - Missing semicolons or braces
# - Incorrect indentation (use 3 spaces per level)
```

### Issue: Connections not auto-starting

**Cause:** Missing `start_action = start` in child SA configuration.

**Solution:**
Ensure each child SA has:
```conf
children {
   aliyun-vpn-master-child {
      ...
      start_action = start
      ...
   }
}
```

---

## Quick Reference Table

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| Tunnel status not `sa_established` | IKE/IPsec parameter mismatch | Compare parameter configs on both ends |
| Phase 1 negotiation failed | PSK inconsistent or IKE params mismatch | Check pre-shared key and IKE config |
| Phase 2 negotiation failed | IPsec param mismatch or subnet config error | Check IPsec config and subnets |
| Tunnel established but ping fails | Routing issue or security group restriction | Check route tables and security group rules |
| Both tunnels UP but routing issues | Priority not configured properly | Set priority=100 for master, priority=200 for slave |
| Connection unstable | DPD config problem or network jitter | Check DPD settings and network quality |
| Cannot establish tunnel behind NAT | NAT traversal not enabled | Configure `local_addrs=%defaultroute` + `encap=yes` |
| swanctl cannot connect to charon | VICI socket not available | Start charon with vici plugin loaded |
