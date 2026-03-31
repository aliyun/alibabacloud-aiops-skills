# StrongSwan Configuration Reference

## Overview

This document describes how to configure StrongSwan using the **VICI (Versatile IKE Configuration Interface)** method with `swanctl.conf`. This is the modern recommended approach that supports both tunnels being UP simultaneously using priority-based routing.

**Why VICI/swanctl instead of ipsec.conf?**
- Supports both tunnels UP at the same time (using `priority` parameter)
- More flexible and modern configuration interface
- Better support for dynamic configuration updates
- Recommended by StrongSwan for new deployments

## Quick Start

See [QUICKSTART.md](strongswan-config-templates/QUICKSTART.md) for complete step-by-step installation and configuration guide with real-world examples.

## Installation

### Ubuntu/Debian
```bash
sudo apt-get update && sudo apt-get install -y strongswan strongswan-swanctl libcharon-extra-plugins
```

### CentOS/RHEL
```bash
sudo yum install -y strongswan strongswan-swanctl
```

### Enable Service
```bash
sudo systemctl enable strongswan
sudo systemctl start strongswan
```

## Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| swanctl.conf | IPsec connection configuration (VICI format) | /etc/swanctl/swanctl.conf |
| strongswan.conf | Global StrongSwan settings with VICI plugin | /etc/strongswan.conf |

## Dual-Tunnel Configuration Templates

See complete working templates in [strongswan-config-templates/](strongswan-config-templates/):
- [swanctl.conf](strongswan-config-templates/swanctl.conf) — Complete dual-tunnel VICI config
- [strongswan.conf](strongswan-config-templates/strongswan.conf) — Global settings with VICI plugin

### Placeholder Reference

Replace these placeholders in the templates with actual values:

| Placeholder | Description | Example |
|--------------|-------------|----------|
| {VPN_GW_IP_1} | Primary VPN GW public IP | 39.106.36.158 |
| {VPN_GW_IP_2} | Backup VPN GW public IP | 39.105.20.65 |
| {SERVER_PUBLIC_IP} | Server's public IP | 203.0.113.10 |
| {LOCAL_SUBNET} | Server-side subnet | 10.0.0.0/24 |
| {REMOTE_SUBNET} | VPC-side subnet | 172.16.0.0/16 |
| {PSK} | Pre-shared key (min 16 chars) | YourStrongPSK... |

#### Key Configuration Points:
1. **`local_addrs=%defaultroute`** — Use current NAT-aware interface (auto-detects public IP)
2. **`encap=yes`** — Enable NAT traversal encapsulation
3. **`priority=100/200`** — Allow both tunnels UP simultaneously; lower value = higher priority
4. **VICI Plugin:** Required in strongswan.conf `load` directive

## Parameter Mapping: Aliyun ↔ StrongSwan

| Alibaba Cloud Param | Aliyun Value | StrongSwan Equivalent |
|---------------------|--------------|----------------------|
| IkeVersion | ikev2 | `version = 2` |
| IkeEncAlg | aes256 | `proposals = aes256-...` |
| IkeAuthAlg | sha256 | `proposals = ...-sha256-...` |
| IkePFS | group14 | `proposals = ...-modp2048` |
| IkeLifetime | 86400 | `rekey_time = 85500s` (slightly less than lifetime) |
| IpsecEncAlg | aes256 | `esp_proposals = aes256-...` |
| IpsecAuthAlg | sha256 | `esp_proposals = ...-sha256-...` |
| IpsecPFS | group14 | `esp_proposals = ...-modp2048` |
| IpsecLifetime | 86400 | `life_time = 86400s` |

### DH Group Reference

| Alibaba Cloud IKE PFS/Ipsec PFS | StrongSwan modp |
|--------------------------------|-----------------|
| group1 | modp768 |
| group2 | modp1024 |
| group5 | modp1536 |
| group14 | modp2048 |

## Pre-Configuration Steps

### 1. Backup Existing Configuration

Before making any changes, backup existing StrongSwan configuration:

```bash
# Backup existing configuration files
sudo cp /etc/swanctl/swanctl.conf /etc/swanctl/swanctl.conf.bak.$(date +%Y%m%d) 2>/dev/null || true
sudo cp /etc/strongswan.conf /etc/strongswan.conf.bak.$(date +%Y%m%d) 2>/dev/null || true

# If using legacy ipsec.conf
sudo cp /etc/ipsec.conf /etc/ipsec.conf.bak.$(date +%Y%m%d) 2>/dev/null || true
sudo cp /etc/ipsec.secrets /etc/ipsec.secrets.bak.$(date +%Y%m%d) 2>/dev/null || true
```

### 2. Verify Configuration Syntax

After writing configuration files, verify syntax before starting service:

```bash
# Load configuration with debug output to check for syntax errors
sudo swanctl --load-all --debug

# If no errors, you should see:
# - "loaded ike secret 'ike-aliyun-master'"
# - "loaded ike secret 'ike-aliyun-slave'"
# - "loaded connection 'aliyun-vpn-master'"
# - "loaded connection 'aliyun-vpn-slave'"
# - "successfully loaded 2 connections, 0 unloaded"
```

### 3. Rollback Procedure

If configuration fails or causes issues, rollback to previous state:

```bash
# Stop StrongSwan service
sudo systemctl stop strongswan-starter

# Restore backup configuration
sudo cp /etc/swanctl/swanctl.conf.bak.* /etc/swanctl/swanctl.conf
sudo cp /etc/strongswan.conf.bak.* /etc/strongswan.conf

# Restart service with old configuration
sudo systemctl start strongswan-starter
sudo swanctl --load-all
```

## Starting and Managing Connections

### Start StrongSwan Daemon

```bash
# Start charon daemon (if not using systemd)
/usr/lib/ipsec/charon &

# Or using systemd (Ubuntu/Debian)
sudo systemctl start strongswan-starter

# Or using systemd (CentOS/RHEL)
sudo systemctl start strongswan
```

**Note:** Service name varies by distribution:
- Ubuntu/Debian: `strongswan-starter`
- CentOS/RHEL: `strongswan`

### Load Configuration

```bash
# Load all connections and secrets from swanctl.conf
sudo swanctl --load-all

# Load only connections
sudo swanctl --load-conns

# Load only secrets
sudo swanctl --load-creds
```

### Initiate Connections

After loading configuration, manually initiate both tunnels:

```bash
# Initiate primary (master) tunnel
sudo swanctl --initiate --child aliyun-vpn-master-child

# Initiate backup (slave) tunnel
sudo swanctl --initiate --child aliyun-vpn-slave-child

# Or initiate all connections at once
sudo swanctl --load-all && \
  sudo swanctl --initiate --child aliyun-vpn-master-child && \
  sudo swanctl --initiate --child aliyun-vpn-slave-child
```

**Note:** Connections with `start_action = start` in the child SA configuration should auto-initiate, but manual initiation ensures immediate establishment.

### Common Diagnostic Commands

| Command | Description |
|---------|-------------|
| `sudo swanctl --list-sas` | View all established Security Associations |
| `sudo swanctl --list-conns` | List all configured connections |
| `sudo swanctl --stats` | Show daemon statistics |
| `sudo swanctl --log` | Show log output |
| `sudo swanctl --terminate --ike aliyun-vpn-master` | Terminate specific connection |
| `sudo swanctl --initiate --child aliyun-vpn-master-child` | Initiate specific child SA |

## Routing

StrongSwan auto-installs routes when `install_routes = yes` is set in strongswan.conf. Verify:

```bash
ip route show | grep -E "{REMOTE_SUBNET}|{LOCAL_SUBNET}"
```

Manual addition (if needed):
```bash
sudo ip route add {REMOTE_SUBNET} via {VPN_GW_IP_1} dev {INTERFACE}
```

## Kernel Parameters

```bash
# Enable IP forwarding (for traffic routing)
sudo sysctl -w net.ipv4.ip_forward=1

# Permanent: Add to /etc/sysctl.conf
# net.ipv4.ip_forward = 1
```

**See [QUICKSTART.md](strongswan-config-templates/QUICKSTART.md) for complete examples.**
