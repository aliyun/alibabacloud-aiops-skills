# StrongSwan Quick Setup Guide (VICI/swanctl Method)

This guide uses the modern **VICI (Versatile IKE Configuration Interface)** method with `swanctl.conf` instead of the legacy `ipsec.conf` format. This enables both tunnels to be UP simultaneously using priority-based routing.

## Tunnel Parameters

| Parameter | Master Tunnel | Backup Tunnel |
|-----------|---------------|---------------|
| **VPN Gateway IP** | 39.106.36.158 | 39.105.20.65 |
| **Server Public IP** | 203.0.113.10 | 203.0.113.10 |
| **PSK** | e6qrIPE1oyY6V2T4wLgb | e6qrIPE1oyY6V2T4wLgb |
| **Local Subnet (VPC)** | 172.16.0.0/16 | 172.16.0.0/16 |
| **Remote Subnet (Server)** | 10.0.0.0/24 | 10.0.0.0/24 |

## IKE/IPsec Configuration Parameters

### Phase 1 (IKE)

| Parameter | Value |
|-----------|-------|
| IKE Version | IKEv2 |
| Encryption Algorithm | AES256 |
| Authentication Algorithm | SHA256 |
| DH Group | Group 14 (modp2048) |
| Lifetime | 86400 seconds (24 hours) |
| Negotiation Mode | Main |

### Phase 2 (IPsec/ESP)

| Parameter | Value |
|-----------|-------|
| Encryption Algorithm | AES256 |
| Authentication Algorithm | SHA256 |
| PFS | Group 14 (modp2048) |
| Lifetime | 86400 seconds (24 hours) |

## Installation Steps

### 1. Install StrongSwan with swanctl

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y strongswan strongswan-swanctl libstrongswan-standard-plugins libcharon-extra-plugins
```

**CentOS/RHEL:**
```bash
sudo yum install -y epel-release
sudo yum install -y strongswan strongswan-swanctl
```

### 2. Configure /etc/strongswan.conf

Copy `references/strongswan-config-templates/strongswan.conf` to `/etc/strongswan.conf`:

```bash
sudo cp references/strongswan-config-templates/strongswan.conf /etc/strongswan.conf
```

Content:
```conf
charon {
    load_modular = yes
    plugins {
        include strongswan.d/charon/*.conf
    }
    load = curl aes des sha1 sha2 md5 pem pkcs1 gmp random nonce hmac kernel-netlink socket-default updown vici
    install_routes = yes
    install_virtual_ip = no
}
include /etc/swanctl/swanctl.conf
include strongswan.d/*.conf
```

### 3. Configure /etc/swanctl/swanctl.conf

Copy `references/strongswan-config-templates/swanctl.conf` to `/etc/swanctl/swanctl.conf`:

```bash
sudo mkdir -p /etc/swanctl
sudo cp references/strongswan-config-templates/swanctl.conf /etc/swanctl/swanctl.conf
sudo chmod 600 /etc/swanctl/swanctl.conf
```

**Important**: Edit the file and replace all placeholder values with your actual configuration.

### 4. Enable IP Forwarding

```bash
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 5. Configure Firewall

```bash
# IKE (UDP 500)
sudo iptables -A INPUT -p udp --dport 500 -j ACCEPT

# NAT-T (UDP 4500)
sudo iptables -A INPUT -p udp --dport 4500 -j ACCEPT

# ESP (Protocol 50)
sudo iptables -A INPUT -p esp -j ACCEPT

# AH (Protocol 51) - optional
sudo iptables -A INPUT -p ah -j ACCEPT
```

### 6. Start StrongSwan

```bash
# Start charon daemon
sudo /usr/lib/ipsec/charon &

# Or using systemd
sudo systemctl enable strongswan
sudo systemctl start strongswan

# Load configuration
sudo swanctl --load-all
```

## Verify Tunnel Status

### Check Tunnel Status

```bash
# List all Security Associations
sudo swanctl --list-sas

# Show detailed statistics
sudo swanctl --stats

# List configured connections
sudo swanctl --list-conns
```

### Expected Output

Successful tunnels should show `ESTABLISHED` state:

```
aliyun-vpn-master: #1, ESTABLISHED, IKEv2, 1234567890abcdef:9876543210fedcba
  local  '203.0.113.10' @ 203.0.113.10[4500]
  remote '39.106.36.158' @ 39.106.36.158[4500]
  AES_CBC-256/HMAC_SHA2_256_128/PRF_HMAC_SHA2_256/MODP_2048
  established 5 minutes ago
  aliyun-vpn-master-child: #1, reqid 1, INSTALLED, TUNNEL, ESP:AES_CBC-256/HMAC_SHA2_256_128
    installed 5 minutes ago
    local  10.0.0.0/24
    remote 172.16.0.0/16

aliyun-vpn-slave: #2, ESTABLISHED, IKEv2, abcdef1234567890:fedcba9876543210
  local  '203.0.113.10' @ 203.0.113.10[4500]
  remote '39.105.20.65' @ 39.105.20.65[4500]
  established 5 minutes ago
  aliyun-vpn-slave-child: #2, reqid 2, INSTALLED, TUNNEL, ESP:AES_CBC-256/HMAC_SHA2_256_128
    local  10.0.0.0/24
    remote 172.16.0.0/16
```

**Note**: With VICI/swanctl and `priority` parameter, both tunnels can be UP simultaneously:
- Master tunnel has `priority = 100` (higher priority, preferred for traffic)
- Slave tunnel has `priority = 200` (lower priority, standby)

### Test Connectivity

```bash
# Ping private IP of ECS inside VPC
ping -c 5 172.16.1.100

# Traceroute
traceroute 172.16.1.100
```

## Common Commands

### swanctl Commands

```bash
# Load all configuration (connections + secrets)
sudo swanctl --load-all

# Load only connections
sudo swanctl --load-conns

# Load only credentials (secrets)
sudo swanctl --load-creds

# List all established SAs
sudo swanctl --list-sas

# List configured connections
sudo swanctl --list-conns

# Show daemon statistics
sudo swanctl --stats

# Terminate specific connection
sudo swanctl --terminate --ike aliyun-vpn-master

# Initiate specific child SA
sudo swanctl --initiate --child aliyun-vpn-master-child

# View logs
sudo swanctl --log

# Watch real-time status
watch -n 5 'sudo swanctl --list-sas'
```

### Systemd Commands

```bash
# Restart StrongSwan
sudo systemctl restart strongswan

# Stop StrongSwan
sudo systemctl stop strongswan

# Start StrongSwan
sudo systemctl start strongswan

# View logs
sudo journalctl -u strongswan-starter -u strongswan -u charon -f
```

## Troubleshooting

### Tunnel Cannot Establish

1. **Check if charon is running**
   ```bash
   ps aux | grep charon
   sudo /usr/lib/ipsec/charon &  # Start if not running
   ```

2. **Check firewall rules**
   ```bash
   sudo iptables -L INPUT -n | grep -E "(500|4500|esp)"
   ```

3. **Verify PSK matches**
   ```bash
   sudo cat /etc/swanctl/swanctl.conf | grep -A3 "secrets"
   ```

4. **Check IKE/IPsec parameters**
   Ensure they match Alibaba Cloud configuration exactly

5. **View logs**
   ```bash
   sudo journalctl -u strongswan-starter -u strongswan -u charon --no-pager -n 50
   sudo swanctl --log
   ```

6. **Check VICI connection**
   ```bash
   sudo swanctl --stats
   # If "connecting to 'unix:///var/run/charon.vici' failed", charon not running
   ```

### DPD Triggers Reconnection

If tunnel frequently reconnects, DPD timeout may be too short. Adjust in swanctl.conf:

```conf
dpd_delay = 30s
dpd_timeout = 300s  # Increase to 5 minutes
```

Then reload:
```bash
sudo swanctl --load-all
```

### Routing Issues

If tunnel establishes but cannot communicate, check routing:

```bash
# View route table
ip route

# Add static route (if needed)
sudo ip route add 172.16.0.0/16 dev <interface>
```

### Both Tunnels UP but Traffic Issues

With VICI/swanctl using `priority` parameter, both tunnels should be UP. If traffic issues occur:

**Check priority configuration:**
```bash
# Master tunnel should have lower priority number (higher priority)
grep -A20 "aliyun-vpn-master" /etc/swanctl/swanctl.conf | grep priority
# Expected: priority = 100

# Slave tunnel should have higher priority number (lower priority)
grep -A20 "aliyun-vpn-slave" /etc/swanctl/swanctl.conf | grep priority
# Expected: priority = 200
```

**Verify both SAs established:**
```bash
sudo swanctl --list-sas
# Both aliyun-vpn-master and aliyun-vpn-slave should show ESTABLISHED
```

## Performance Optimization

### 1. Increase File Descriptor Limits

Add in `/etc/systemd/system/strongswan.service.d/override.conf`:

```ini
[Service]
LimitNOFILE=65536
```

### 2. Enable Hardware Encryption (if supported)

```bash
# Check if AES-NI is supported
grep -i aesni /proc/cpuinfo

# Load related modules
sudo modprobe aesni_intel
sudo modprobe crypto_simd
```

### 3. Adjust Kernel Parameters

Add to `/etc/sysctl.conf`:

```conf
net.core.netdev_max_backlog = 5000
net.core.xfrm_aevent_rmtth = 10
net.core.xfrm_aevent_etime = 100
```

## Monitoring and Alerting

### Use Monitoring Script

```bash
#!/bin/bash
# monitor-tunnels.sh

established=$(swanctl --list-sas 2>/dev/null | grep -c "ESTABLISHED")
if [ "$established" -lt 2 ]; then
    echo "WARNING: Not all IPsec tunnels established! ($established/2)"
    # Send alert email/SMS
    # mail -s "IPsec Tunnel Down" admin@example.com <<< "Only $established/2 tunnels up"
fi
```

### Add to crontab

```bash
*/5 * * * * /path/to/monitor-tunnels.sh
```

## Backup and Recovery

### Backup Configuration

```bash
tar -czvf strongswan-backup-$(date +%Y%m%d).tar.gz \
    /etc/swanctl/swanctl.conf \
    /etc/strongswan.conf \
    /etc/systemd/system/strongswan.service.d/
```

### Restore Configuration

```bash
tar -xzvf strongswan-backup-YYYYMMDD.tar.gz -C /
sudo swanctl --load-all
```

## Security Recommendations

1. **Rotate PSK regularly**: Change pre-shared key every 90 days
2. **Use strong passwords**: PSK minimum 20 characters, including uppercase, lowercase, numbers, special characters
3. **Restrict access**: Only allow necessary IP addresses through tunnel
4. **Enable logging**: Record all IPsec events for audit
5. **Monitor traffic**: Use tcpdump or Wireshark to analyze suspicious traffic
6. **File permissions**: Ensure swanctl.conf has restricted permissions (chmod 600)

## Support & Contact

For questions, refer to:
- StrongSwan Official Documentation: https://docs.strongswan.org/
- StrongSwan VICI Documentation: https://docs.strongswan.org/docs/5.9/plugins/vici.html
- Alibaba Cloud VPN Gateway Documentation: https://help.aliyun.com/product/26178.html
