# SSH Remote Execution Details

This file supplements the "remote execution" mode in SKILL.md. All commands run in the **local terminal** and operate the remote server via SSH.

## SSH connection format

> All SSH commands must carry timeout parameters to prevent the Agent from blocking indefinitely.

```bash
# Key authentication (recommended)
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 -i ~/.ssh/id_rsa -p 22 USER@HOST 'COMMAND'

# Password authentication (requires interactive input)
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 -p 22 USER@HOST 'COMMAND'

# Passwordless login setup (one-time; afterwards no -i parameter needed)
ssh-copy-id -i ~/.ssh/id_rsa.pub USER@HOST
```

> **Warning**: Key file permission requirement: the private key must be 600 or 400, otherwise SSH refuses to use it.
> ```bash
> chmod 600 ~/.ssh/id_rsa
> chmod 644 ~/.ssh/id_rsa.pub
> ```

---

## Upload files to the remote server

```bash
# Upload the config file
scp -o ConnectTimeout=10 /local/path/shake.toml USER@HOST:/opt/redis-shake/shake.toml

# Set secure permissions after upload
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'chmod 600 /opt/redis-shake/shake.toml'

# First-time deployment: upload the binary
scp -o ConnectTimeout=10 redis-shake USER@HOST:/opt/redis-shake/redis-shake
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'chmod +x /opt/redis-shake/redis-shake && mkdir -p /opt/redis-shake/data'
```

---

## Operation commands (remote version)

### Start

```bash
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'cd /opt/redis-shake && mkdir -p data && if [ -f data/shake.pid ] && kill -0 $(cat data/shake.pid) 2>/dev/null; then echo "Already running"; exit 1; fi && nohup ./redis-shake shake.toml > data/shake.log 2>&1 & echo $! > data/shake.pid && echo "Started, PID: $(cat data/shake.pid)"'
```

### Stop

```bash
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'PID=$(cat /opt/redis-shake/data/shake.pid 2>/dev/null); [ -n "$PID" ] && kill "$PID" && rm -f /opt/redis-shake/data/shake.pid && echo "Stopped" || echo "Not running"'
```

### Check status

```bash
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'PID_FILE=/opt/redis-shake/data/shake.pid; [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null && echo "RUNNING, PID: $(cat $PID_FILE)" || echo "STOPPED"'
```

### View logs

```bash
# View the latest 100 lines
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'tail -100 /opt/redis-shake/data/shake.log'

# Follow in real time (auto-exit after 60s timeout)
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'timeout 60 tail -f /opt/redis-shake/data/shake.log'

# Filter key metrics
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'grep -E "entries|qps|rdb|aof|error|ERR" /opt/redis-shake/data/shake.log | tail -30'
```

### Restart

```bash
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'cd /opt/redis-shake && PID=$(cat data/shake.pid 2>/dev/null); [ -n "$PID" ] && kill "$PID" && sleep 2; rm -f data/shake.pid; nohup ./redis-shake shake.toml > data/shake.log 2>&1 & echo $! > data/shake.pid && echo "Restarted"'
```

---

## systemd remote configuration

> **Warning**: Requires root permission on the target server; the `-t` flag allocates a pseudo-terminal to support sudo.

```bash
# Write the service file
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 -t USER@HOST 'sudo tee /etc/systemd/system/redis-shake.service > /dev/null << "EOF"
[Unit]
Description=RedisShake Data Migration
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/redis-shake
ExecStart=/opt/redis-shake/redis-shake shake.toml
Restart=on-failure
RestartSec=5s
StandardOutput=append:/opt/redis-shake/data/shake.log
StandardError=append:/opt/redis-shake/data/shake.log

[Install]
WantedBy=multi-user.target
EOF'

# Enable and start the service
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 -t USER@HOST 'sudo systemctl daemon-reload && sudo systemctl enable redis-shake && sudo systemctl start redis-shake && sudo systemctl status redis-shake'
```

---

## Batch operations across multiple servers

```bash
HOSTS=("192.168.1.101" "192.168.1.102" "192.168.1.103")
USER=root
SSH_OPTS="-o ConnectTimeout=10 -o ServerAliveInterval=30"

# Batch check status
for HOST in "${HOSTS[@]}"; do
    echo "=== $HOST ==="
    ssh $SSH_OPTS $USER@$HOST 'PID_FILE=/opt/redis-shake/data/shake.pid; [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null && echo "RUNNING" || echo "STOPPED"'
done

# Batch start
for HOST in "${HOSTS[@]}"; do
    echo "=== Starting on $HOST ==="
    ssh $SSH_OPTS $USER@$HOST 'cd /opt/redis-shake && mkdir -p data && if [ -f data/shake.pid ] && kill -0 $(cat data/shake.pid) 2>/dev/null; then echo "Already running"; else nohup ./redis-shake shake.toml > data/shake.log 2>&1 & echo $! > data/shake.pid && echo "Started"; fi'
done

# Batch stop
for HOST in "${HOSTS[@]}"; do
    echo "=== Stopping on $HOST ==="
    ssh $SSH_OPTS $USER@$HOST 'PID=$(cat /opt/redis-shake/data/shake.pid 2>/dev/null); [ -n "$PID" ] && kill "$PID" && rm -f /opt/redis-shake/data/shake.pid && echo "Stopped" || echo "Not running"'
done
```

---

## HTTP monitoring remote access

Access remote metrics locally via SSH port forwarding:

```bash
# Establish port forwarding (run in background)
ssh -o ConnectTimeout=10 -L 18080:localhost:8080 USER@HOST -N &

# Access remote metrics
curl http://localhost:18080/metrics

# Close port forwarding
kill %1
```

---

## Common SSH troubleshooting

| Symptom | Investigation steps |
|------|---------|
| Connection timeout | Check whether the firewall allows the SSH port; `ssh -v USER@HOST` to view detailed logs |
| Password prompt stalls the script | Configure SSH key passwordless login: `ssh-copy-id USER@HOST` |
| sudo command stalls (needs password) | Add the `-t` flag to allocate a pseudo-terminal, or configure passwordless sudoers |
| Single-quote conflict in remote command | Use `$'...'` syntax or pass via heredoc through a pipe |
| nohup process exits when SSH disconnects | Confirm `&` is used and output is redirected, or switch to `screen` / `tmux` |
