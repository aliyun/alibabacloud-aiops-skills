# Server-side Pre-check

Before creating Alibaba Cloud resources, must verify server-side configuration and permissions.

Choose corresponding pre-check method based on deployment mode:

## Option A: Local Mode Pre-check

Applicable for scenarios where configuration happens directly on current server.

### 1. Check System Administrator Privileges

```bash
whoami && id
```

- If `root` user: can execute system config commands directly
- If regular user: need to verify sudo privileges
  ```bash
  sudo -n whoami
  ```
  If returns `root`, indicates passwordless sudo privilege; otherwise password required later

### 2. Verify Network Configuration Capability

```bash
ping -c 3 8.8.8.8 && curl -sI --connect-timeout 5 https://www.aliyun.com | head -1
```

Expected: Ping test passes AND HTTPS request succeeds

### 3. Check OS Type

```bash
cat /etc/os-release | grep -E '^(ID|VERSION_ID)='
```

Select package manager based on system type: Ubuntu/Debian use `apt-get`, CentOS/RHEL use `yum`

### 4. Check Network Interfaces and Routing

```bash
ip addr show | grep -E '^[0-9]+:|inet '
ip route show default
```

Record primary network interface name, private IP, and default gateway for later configuration

---

## Option B: SSH Remote Mode Pre-check

Applicable for scenarios managed via SSH remote administration. Connect to server through SSH and perform same checks as "Local Mode Pre-check".

Simply add `ssh -i {SSH_KEY_PATH} {SERVER_LOGIN_USER}@{SERVER_PUBLIC_IP}` prefix before each command.
