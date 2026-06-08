# Step-by-Step Tutorial: Deploy a Python Flask App

> A concrete walk-through that satisfies SHOULD 1.2.4. The example shows the inputs the Agent should send and the expected outputs at each step. Use this together with the workflow rules in [SKILL.md](../SKILL.md).

## Prerequisites

- Local project at `~/projects/my-flask-app/` containing `app.py` and `requirements.txt`.
- Alibaba Cloud account with the default credential chain configured (RAM Role / env vars / `~/.aliyun/config.json`).
- `python3` available; the `aliyun` CLI may or may not be installed (Step 2 takes care of it).

## Step 1: Enter the project directory

Input:
```bash
cd ~/projects/my-flask-app && ls
```

Expected output:
```
Dockerfile  README.md  app.py  requirements.txt
```

## Step 2: Resolve `$SKILL_DIR` and run environment check

Input:
```bash
export SKILL_DIR="$HOME/.qoder/skills/alibabacloud-ecs-code-deploy"
test -f "$SKILL_DIR/scripts/deploy_toolkit.py" && echo OK
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check
```

Expected output (success path):
```
OK
=== Environment Check ===
✅ aliyun CLI: 3.3.19 (>=3.3.19) [active: /usr/local/bin/aliyun]
✅ appmanager-cli: 1.1.1 (>=1.1.1)
✅ credentials: profile=default region=cn-beijing ak=LTAI***abcd
=== Environment Check Done ===

✅ All checks passed. Ready to deploy.
```

If any check exits 1, follow the script's `→ AGENT: DO NOT stop. ASK user ...` hint verbatim before proceeding.

## Step 3: Initialize `.appmanager/config.yaml`

Ask the user for region + ECS target (see Task 3 in SKILL.md), then run:
```bash
aliyun appmanager init --non-interactive \
  --name my-flask-app \
  --type app \
  --region cn-beijing \
  --port 8080
```

Expected: `.appmanager/config.yaml` is created. Edit it to add `common.scripts.start` / `common.scripts.stop`. Key fragment:
```yaml
metadata:
  name: my-flask-app
  type: app
  groupName: default-cn-beijing
  regionId: cn-beijing
common:
  deployment:
    ecsInstanceType: ecs.u1-c1m2.large
    systemDiskSize: 40
    internetMaxBandwidthOut: 5
  scripts:
    start: |
      #!/bin/bash
      set -e
      command -v unzip >/dev/null || yum install -y unzip
      ZIP=$(find /root -maxdepth 2 -name 'my-flask-app*.zip' | head -1)
      mkdir -p /root/my-flask-app && unzip -o "$ZIP" -d /root/my-flask-app
      cd /root/my-flask-app
      command -v python3 >/dev/null || yum install -y python3
      pip3 install -r requirements.txt
      [ -f /root/app.pid ] && kill "$(cat /root/app.pid)" 2>/dev/null || true
      nohup python3 app.py >> /root/app.log 2>&1 &
      echo $! > /root/app.pid
      sleep 3 && cat /root/app.log
    stop: |
      #!/bin/bash
      [ -f /root/app.pid ] && kill "$(cat /root/app.pid)" 2>/dev/null || true
```

## Step 4: Pre-deploy price check + user confirmation

Input:
```bash
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" price --config .appmanager/config.yaml
```

Expected output (excerpt — the Agent must relay both the price block and the OSS notice to the user):
```
==================================================
📊 Deployment Price Estimate
==================================================
Region        : cn-beijing
...
💰 Total: CNY 0.06000/hour
   Monthly estimate: CNY 43.20/month (30 days x 24 hours)
==================================================

📦 OSS extra billing (not covered by `appmanager price`; relay to the user):
    - OSS standard storage: ~CNY 0.12/GB/month ...
=== AGENT_CONFIRM_REQUIRED ===
```

Agent then asks the user (example wording — see Task 4.5 in SKILL.md): "Estimated cost: CNY 0.06/hour (~CNY 43.20/month); the deployment also incurs minor OSS storage/request fees. Confirm to continue?"

## Step 5: Deploy and verify

Input:
```bash
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" deploy \
  --type app --name my-flask-app --group default-cn-beijing --region cn-beijing
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" verify \
  --type app --name my-flask-app --group default-cn-beijing --region cn-beijing --wait 10
```

Expected (success):
```
--- Deploy command completed (exit 0) ---
✅ Deploy submitted. Use 'deploy_toolkit.py verify' to check if app is actually running.
...
=== Post-deploy Verification ===
ECS Public IP: 47.95.xxx.xxx
--- Application Log (source: cloud_assistant) ---
 * Serving Flask app 'app'
 * Running on http://0.0.0.0:8080
=== AGENT_ANALYZE_REQUIRED ===
log_source: cloud_assistant
ecs_instance: i-2zexxxxxxxxxxxxxxxxxxx
```

The Agent then prints the self-check report and the final output (console link + cost reminder + management commands).

## Edge cases

| Situation | What to do |
|-----------|-----------|
| `ReleaseCancelled` returned by deploy | The start script failed/timed out on ECS. Run `verify` -> read `/root/app.log` -> fix the start script -> redeploy (max 3 retries). |
| `NotEnoughBalance` error | Pay-as-you-go ECS requires balance >= CNY 100. Direct the user to https://usercenter2.aliyun.com/finance/fund-management or switch to existing ECS. |
| `AccessDenied` at `upload_to_oss` | OSS bucket name `<app_name>-<region>` is globally unique. Change `--name` to a more unique value, delete `.appmanager/`, and re-init + redeploy. |
| Existing-ECS impact warning | Ask the user explicitly: deploying may stop/overwrite other apps on the instance. STOP if user refuses. |
| Cloud Assistant log fetch fails | Surface the SSH fallback `ssh root@<ECS_IP> 'tail -100 /root/app.log'` and the HTTP port probe result printed by `verify`. |
