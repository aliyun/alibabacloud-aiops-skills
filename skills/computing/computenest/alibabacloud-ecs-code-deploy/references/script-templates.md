# Script Templates & Language Reference

## Start Script Template (Generic)

> Replace `{app_name}` with the actual `--name` value used in `init`. Replace `{INSTALL_RUNTIME}`, `{INSTALL_DEPS}`, `{START_CMD}` with language-specific commands from the Language Reference Table below.

```bash
#!/bin/bash
set -e
APP_DIR=/root/{app_name}
ZIP_FILE=$(ls /root/project_*.zip 2>/dev/null | tail -1)
LOG_FILE=/root/app.log
PID_FILE=/root/app.pid

# Stop existing process
[ -f "$PID_FILE" ] && kill "$(cat $PID_FILE)" 2>/dev/null || true
rm -f "$PID_FILE"

# Detect package manager
if command -v dnf &>/dev/null; then
  PKG_MGR="dnf"
elif command -v yum &>/dev/null; then
  PKG_MGR="yum"
elif command -v apt-get &>/dev/null; then
  PKG_MGR="apt-get"
else
  echo "ERROR: No supported package manager found" && exit 1
fi

# Install unzip if missing
if ! command -v unzip &>/dev/null; then
  $PKG_MGR install -y unzip
fi

# {INSTALL_RUNTIME} — see Language Reference Table below

# Decompress (MANDATORY — appmanager uploads zip but does NOT extract)
mkdir -p "$APP_DIR"
[ -n "$ZIP_FILE" ] && unzip -o "$ZIP_FILE" -d "$APP_DIR"

cd "$APP_DIR"

# {INSTALL_DEPS} — see Language Reference Table below

# Start
nohup {START_CMD} >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

# MANDATORY: output log for verification
sleep 3 && cat /root/app.log
```

## Language Reference Table

> **⚠️ Supply chain security**: Some rows below use `curl ... | bash` or `curl ... | php` patterns to install runtimes. These are convenience patterns from upstream vendors (NodeSource, Composer, Go) — they execute remote code without local verification and are vulnerable to MITM/supply-chain attacks if the source is compromised. Mitigations applied below:
> - **NodeSource (Node.js)**: HTTPS-only, official `nodesource.com` domain. For high-security environments, prefer the distro package: `dnf module install -y nodejs:22` (RHEL 9) / `apt-get install -y nodejs npm`.
> - **Go**: SHA256 checksum verification added before extraction. Reject if mismatch.
> - **Composer**: SHA-384 installer signature verification added (per upstream guidance at https://getcomposer.org/download/). Reject and abort if signature mismatch.
> - **All `/usr/local` writes**: Run as root inside ECS deploy context (start script executes as root via Cloud Assistant). Outside ECS, prepend `sudo`.

| Language | Check | Install Runtime (RHEL/yum) | Install Runtime (Debian/apt) | Install Deps | Start Command |
|----------|-------|---------------------------|------------------------------|--------------|---------------|
| **Python** | `command -v pip3` | `$PKG_MGR install -y python3 python3-pip` | `apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv` | `pip3 install -r requirements.txt -q` or `pip3 install -e . -q` | `python3 main.py` |
| **Node.js** | `command -v node` | `curl --connect-timeout 30 --max-time 120 -fsSL https://rpm.nodesource.com/setup_22.x \| bash - && $PKG_MGR install -y nodejs` (HTTPS official NodeSource; prefer distro package for stricter envs) | `curl --connect-timeout 30 --max-time 120 -fsSL https://deb.nodesource.com/setup_22.x \| bash - && apt-get install -y -qq nodejs` | `npm install --production` or `pnpm install --frozen-lockfile && pnpm build` | `node dist/index.js` or `npm start` |
| **Java** | `command -v java` | `$PKG_MGR install -y java-17-openjdk` | `apt-get update -qq && apt-get install -y -qq default-jdk` | N/A (pre-built JAR) | `java -jar $(find $APP_DIR -name "*.jar" \| head -1)` |
| **Go** | `command -v go` | See **Go install snippet** below (with SHA256 verification) | (same) | `go build -o app .` (if source) or N/A (pre-compiled) | `./app` or `$(find $APP_DIR -type f -perm /111 -not -name "*.sh" \| head -1)` |
| **PHP** | `command -v php` | `$PKG_MGR install -y php php-cli php-mbstring php-xml` + see **Composer install snippet** below (with signature verification) | `apt-get update -qq && apt-get install -y -qq php php-cli php-mbstring php-xml composer` | `composer install --no-dev --optimize-autoloader` | `php artisan serve --host=0.0.0.0 --port=8080` |
| **Docker** | (pre-installed on ECS) | N/A | N/A | N/A | `docker compose up -d` (no PID/nohup needed) |

> **Pattern**: Wrap runtime install in `if ! {Check} &>/dev/null; then ... fi` for idempotency. For Go on China ECS, MUST use `golang.google.cn` mirror and set `GOPROXY=https://goproxy.cn,direct`.

### Go install snippet (with SHA256 verification)

```bash
GO_VERSION=1.22.0
GO_TGZ=go${GO_VERSION}.linux-amd64.tar.gz
# SHA256 from https://go.dev/dl/  (update when bumping GO_VERSION)
GO_SHA256=f6c8a87aa03b92c4b0bf3d558e28ea03006eb29db78917daec5cfb6ec1046265
curl --connect-timeout 30 --max-time 120 -fsSLO https://golang.google.cn/dl/${GO_TGZ}
echo "${GO_SHA256}  ${GO_TGZ}" | sha256sum -c - || { echo "Go checksum mismatch — refusing to install" >&2; exit 1; }
tar -C /usr/local -xzf ${GO_TGZ} && rm -f ${GO_TGZ}
export PATH=$PATH:/usr/local/go/bin
export GOPROXY=https://goproxy.cn,direct
```

### Composer install snippet (with signature verification)

Follows official guidance at <https://getcomposer.org/download/>:

```bash
EXPECTED_CHECKSUM=$(curl --connect-timeout 30 --max-time 60 -fsS https://composer.github.io/installer.sig)
curl --connect-timeout 30 --max-time 60 -fsSO https://getcomposer.org/installer
ACTUAL_CHECKSUM=$(php -r "echo hash_file('sha384', 'installer');")
if [ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ]; then
    echo "Composer installer signature mismatch — aborting" >&2
    rm -f installer
    exit 1
fi
php installer --install-dir=/usr/local/bin --filename=composer
rm -f installer
```

## Stop Script Template

> **CRITICAL**: Stop script MUST NOT contain `exit 0` or any `exit` statement. The deploy system concatenates stop+start into a single shell execution. If stop script has `exit`, the start script will NEVER run and deployment will produce zero logs.

> **Safety notes**:
> - **Graceful-then-force termination**: The script first sends `SIGTERM` (`kill "$PID"`) and waits 3 seconds for the process to flush state and exit cleanly. `kill -9` (SIGKILL) is only used as a fallback when graceful termination fails. Do NOT remove the 3-second grace window — long-running processes may need time to flush data.
> - **Destructive cleanup guard**: `rm -rf "$APP_DIR"` is dangerous if `$APP_DIR` is empty or set to a wrong path (e.g. `/`). The template includes hard guards: `[ -n "$APP_DIR" ]`, `$APP_DIR` length check, and a strict prefix check (`/root/<app_name>`). Do NOT loosen these.

```bash
#!/bin/bash
PID_FILE=/root/app.pid
APP_DIR=/root/{app_name}

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        # Graceful shutdown first — give the process 3s to flush state
        kill "$PID"
        sleep 3
        # Fallback: force-kill ONLY if still alive after grace period
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
    fi
    rm -f "$PID_FILE"
fi

# Clean up project directory for re-deploy.
# Hard guards prevent catastrophic deletion if APP_DIR is empty or misconfigured.
if [ -n "$APP_DIR" ] && [ "${#APP_DIR}" -gt 6 ] && [[ "$APP_DIR" == /root/* ]] && [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi
# DO NOT add "exit 0" here — it will kill the entire deployment process
```

## Writing Scripts to config.yaml

After generating scripts, the Agent MUST write them into `.appmanager/config.yaml` under `common.scripts`:

> **CRITICAL**: The deploy system ONLY reads `common.scripts.start` and `common.scripts.stop`.
> A top-level `scripts:` key is IGNORED. If scripts are placed at the wrong level, deployment will use the auto-generated default scripts (which will fail).

**Recommended method — use Python yaml library** (avoids YAML formatting issues):

```python
import yaml
config_path = '.appmanager/config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

config['common']['scripts'] = {
    'start': '#!/bin/bash\nset -e\n...',
    'stop': '#!/bin/bash\n...'
}

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
```

**Resulting YAML structure (correct)**:

```yaml
common:
  deployment:
    ecsInstanceType: ecs.u1-c1m2.large
    ...
  scripts:
    start: |
      #!/bin/bash
      set -e
      APP_DIR=/root/my-app
      ...
    stop: |
      #!/bin/bash
      PID_FILE=/root/app.pid
      ...
```

**WRONG structure (deploy system IGNORES this)**:

```yaml
common:
  deployment: ...
scripts:    # ← WRONG! Top-level key, NOT read by deploy system
  start: ...
  stop: ...
```

## Docker Image Accessibility Check (MANDATORY for Docker projects)

When a project contains `docker-compose.yml` or `Dockerfile`, the Agent MUST check whether the required Docker images are accessible from China ECS with mirror acceleration before choosing the Docker deployment path.

**Step 1: Identify required images**

Scan `Dockerfile` for `FROM` directives and `docker-compose.yml` for `image:` fields. Extract all image references (e.g., `node:24-bookworm`, `oven/bun:1.3.13`, `python:3.12-slim`).

**Step 2: Assess China accessibility**

| Image Source | Accessible via China Mirrors? | Action |
|-------------|-------------------------------|--------|
| Official Docker Hub images (`library/*` like `node`, `python`, `nginx`, `redis`, `postgres`) | YES — available on Aliyun/Tencent mirrors | Use Docker with mirror config |
| Popular third-party images (`mysql`, `mongo`, `elasticsearch`) | LIKELY YES | Use Docker with mirror config |
| Niche/uncommon images (`oven/bun`, custom registries, `ghcr.io/*`, `quay.io/*`) | NO — China mirrors don't mirror these | **Fallback to native build** |
| Images pinned by SHA256 digest (`image@sha256:abc...`) | RISKY — mirrors may not resolve digests | **Fallback to native build** |

**Step 3: Decision**

- If ALL images are accessible → Use Docker Compose / Dockerfile deployment with China mirror configuration.
- If ANY image is NOT accessible → **Fallback to native build** (install runtime, build from source, run directly).

**Docker mirror configuration (MUST include in start script when using Docker):**

> **⚠️ System config modification**: This step writes to `/etc/docker/daemon.json` (system-level, requires root). The snippet below performs a **safe merge** that preserves any existing keys (e.g. `data-root`, `log-driver`) and creates a timestamped backup before any change. Do NOT use a naive `printf > daemon.json` that would clobber existing config.

```bash
# Configure China Docker registry mirrors (safe merge, preserves existing config)
mkdir -p /etc/docker
DAEMON_JSON=/etc/docker/daemon.json
MIRRORS='["https://registry.cn-hangzhou.aliyuncs.com", "https://mirror.ccs.tencentyun.com"]'

if [ -f "$DAEMON_JSON" ]; then
    # Backup existing config with timestamp
    cp -p "$DAEMON_JSON" "${DAEMON_JSON}.bak.$(date +%Y%m%d%H%M%S)"
    # Merge: only add registry-mirrors if missing or empty
    python3 -c "
import json, sys
p = '$DAEMON_JSON'
try:
    with open(p) as f: cfg = json.load(f)
except Exception:
    cfg = {}
mirrors = json.loads('$MIRRORS')
existing = cfg.get('registry-mirrors') or []
# Union without duplicates, preserve order
for m in mirrors:
    if m not in existing:
        existing.append(m)
cfg['registry-mirrors'] = existing
with open(p, 'w') as f: json.dump(cfg, f, indent=2)
"
else
    printf '{"registry-mirrors": %s}\n' "$MIRRORS" > "$DAEMON_JSON"
fi

# Reload Docker only if config actually changed
systemctl restart docker
sleep 3
```

> **IMPORTANT**: Even with mirrors configured, SHA256-pinned images and niche registries (oven/bun, ghcr.io) will FAIL. Always fallback to native build in those cases.
