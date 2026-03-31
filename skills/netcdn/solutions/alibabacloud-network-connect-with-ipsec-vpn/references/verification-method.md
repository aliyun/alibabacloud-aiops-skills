# Verification Method

## Verification Steps

### Step 1: Verify VPN Gateway Status

```bash
# Query VPN gateway status, confirm it's active
aliyun vpc describe-vpn-gateway \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-gateway-id {VPN_GATEWAY_ID} \
  --cli-query 'Status' \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected result: `active`

### Step 2: Verify VPN Gateway Public IPs

```bash
# Query VPN gateway details, get both public IPs
aliyun vpc describe-vpn-gateway \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-gateway-id {VPN_GATEWAY_ID} \
  --cli-query '{InternetIp: InternetIp, DisasterRecoveryInternetIp: DisasterRecoveryInternetIp}' \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected result: Returns two different public IP addresses

### Step 3: Verify Customer Gateway

```bash
# Query customer gateways
aliyun vpc describe-customer-gateways \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected result: List contains customer gateway matching server's public IP

### Step 4: Verify IPsec Connection Status

```bash
# Query IPsec connection status
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected result:
- Connection exists and configured correctly
- In dual-tunnel mode, `TunnelOptionsSpecification` contains two tunnel records

### Step 5: Verify IPsec Tunnel Negotiation Status

**Important**: Must perform real verification, NO simulated data allowed.

```bash
# Query IPsec connection details, check dual-tunnel status
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --cli-query 'VpnConnections.VpnConnection[].TunnelOptionsSpecification.TunnelOptions[]' \
  --user-agent AlibabaCloud-Agent-Skills

# Or view full output without cli-query filter
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```

Expected results:
- Both tunnels have `State` = `active`
- Before StrongSwan starts: `Status` = `ike_sa_not_established` (normal)
- After StrongSwan starts: `Status` = `ipsec_sa_established` (both IKE SA and IPsec SA established)
- Verify `TunnelIkeConfig` and `TunnelIpsecConfig` params match configuration exactly

### Step 6: Verify Server-side StrongSwan Status

**Important**: Must view actual output, no simulation allowed.

```bash
# Check IPsec status on server using swanctl
sudo swanctl --list-sas
```

Expected output example (REAL output):
```
aliyun-vpn-master: #1, ESTABLISHED, IKEv2, 1234567890abcdef:9876543210fedcba
  local  '203.0.113.10' @ 203.0.113.10[4500]
  remote '39.106.36.158' @ 39.106.36.158[4500]
  AES_CBC-256/HMAC_SHA2_256_128/PRF_HMAC_SHA2_256/MODP_2048
  established 5 minutes ago
  aliyun-vpn-master-child: #1, reqid 1, INSTALLED, TUNNEL, ESP:AES_CBC-256/HMAC_SHA2_256_128
    installed 5 minutes ago
    in  c8f8f8f8... (0 bytes, 0 packets)
    out c9f9f9f9... (0 bytes, 0 packets)
    local  10.0.0.0/24
    remote 172.16.0.0/16

aliyun-vpn-slave: #2, ESTABLISHED, IKEv2, abcdef1234567890:fedcba9876543210
  local  '203.0.113.10' @ 203.0.113.10[4500]
  remote '39.105.20.65' @ 39.105.20.65[4500]
  AES_CBC-256/HMAC_SHA2_256_128/PRF_HMAC_SHA2_256/MODP_2048
  established 5 minutes ago
  aliyun-vpn-slave-child: #2, reqid 2, INSTALLED, TUNNEL, ESP:AES_CBC-256/HMAC_SHA2_256_128
    installed 5 minutes ago
    in  d0g0g0g0... (0 bytes, 0 packets)
    out d1h1h1h1... (0 bytes, 0 packets)
    local  10.0.0.0/24
    remote 172.16.0.0/16
```

Both tunnels must show `ESTABLISHED` status.

Alternative detailed statistics:
```bash
sudo swanctl --stats
```

### Step 7: Verify Connectivity (Ping Test)

**Important**: Must perform real Ping test.

```bash
# Ping ECS instance in Alibaba Cloud VPC from server side
ping -c 5 {VPC_ECS_PRIVATE_IP}

# Expected output:
# 5 packets transmitted, 5 received, 0% packet loss
```

**If Ping fails, must troubleshoot**:
- Check StrongSwan logs: `sudo journalctl -u strongswan-starter -u strongswan -u charon -f`
- Check firewall rules: `sudo iptables -L INPUT -n | grep -E "(500|4500|esp)"`
- Verify PSK matches: Check secrets in `/etc/swanctl/swanctl.conf`
- Check VICI connection: `sudo swanctl --stats`

### Step 8: View IPsec Connection Logs

**Important**: For dual-tunnel mode VPN connections, must specify each tunnel's TunnelId separately.

```bash
# Query primary tunnel (master) logs
aliyun vpc describe-vpn-connection-logs \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --tunnel-id {TUNNEL_ID_MASTER} \
  --minute-period 60 \
  --user-agent AlibabaCloud-Agent-Skills

# Query backup tunnel (slave) logs
aliyun vpc describe-vpn-connection-logs \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --tunnel-id {TUNNEL_ID_SLAVE} \
  --minute-period 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

**How to obtain TunnelId**:
```bash
# First query VPN connection details to get both tunnel IDs
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --cli-query 'VpnConnections.VpnConnection[].TunnelOptionsSpecification.TunnelOptions[].{TunnelId: TunnelId, Role: Role}' \
  --user-agent AlibabaCloud-Agent-Skills

# Or view full output to find TunnelIds
aliyun vpc describe-vpn-connections \
  --region {REGION_ID} --biz-region-id {REGION_ID} \
  --vpn-connection-id {VPN_CONNECTION_ID} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected results**:
- Logs show normal DPD (Dead Peer Detection) heartbeat information
- No error logs (such as authentication failure, negotiation timeout, etc.)
- Log level typically [INFO] or [DEBUG]

Expected: No error messages in logs, showing normal negotiation and heartbeat records

## Additional VICI/swanctl Verification Commands

### List All Configured Connections
```bash
sudo swanctl --list-conns
```

### Check Loaded Credentials (Secrets)
```bash
sudo swanctl --list-creds
```

### View Detailed Connection Info
```bash
sudo swanctl --show-sa --ike aliyun-vpn-master
```

### Monitor Real-time Logs
```bash
sudo swanctl --log
```

## Common Troubleshooting

See [troubleshooting.md](troubleshooting.md#quick-reference-table) for the complete troubleshooting reference table.
