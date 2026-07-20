# Deploy Modes

## InstallApplication

Provide `regionId`, `instanceIds`, `appName`, `artifactPath`, and either `artifactUrl` or `filePath`:

```bash
cadt-deploy-on-aliyun -run InstallApplication '{
  "regionId": "cn-hangzhou",
  "instanceIds": ["i-xxx", "i-yyy"],
  "appName": "my-app",
  "artifactUrl": "oss://bucket/path/to/artifact.tar.gz",
  "applicationStart": "scripts/start.sh",
  "applicationStop": "scripts/stop.sh",
  "artifactPath": "/root/my-app-deploy",
  "installPath": "/root/my-app"
}'
```

**Required parameters**: `regionId`, `instanceIds`, `appName`, `applicationStart`, `applicationStop`, `artifactPath`, and either `artifactUrl` or `filePath`

**Optional parameters**: `installPath` (default `/root/{appName}`), `ossRegion`, `skipRollback`, `deployTimeout`

## Deployment Package Structure

The deployment package (passed via `filePath` or `artifactUrl`) **MUST** be a `.tar.gz` archive with a **flat** internal structure (no nested top-level directory):

```
my-app-deploy.tar.gz
├── scripts/
│   ├── start.sh      # startup script (background mode: nohup/setsid/screen/--daemon)
│   └── stop.sh       # stop script (kill by PID file)
├── app.jar            # or app.whl / binary / any application artifact
└── ...                # additional files as needed
```

> Single `.jar` / `.war` / `.whl` / `.tgz` files are **NOT** supported as `filePath` directly. They must be repackaged into a `.tar.gz` that includes the `scripts/` directory. See [step-2] §2.3 for the repackaging procedure.

**Forbidden: nested top-level directory**

The tar.gz must NOT contain a wrapper directory at the root. The deployment system extracts the archive directly into `artifactPath`; a nested top-level directory shifts all paths by one level and breaks `scripts/start.sh` resolution.

```
# WRONG — tar created with a wrapper directory
my-app-deploy.tar.gz
└── my-app-deploy/          # ← nested top-level dir, breaks path resolution
    ├── scripts/
    │   ├── start.sh        #   actual path: my-app-deploy/scripts/start.sh
    │   └── stop.sh         #   expected:    scripts/start.sh  ← MISMATCH
    └── app.jar

# CORRECT — flat structure (no wrapper directory)
my-app-deploy.tar.gz
├── scripts/
│   ├── start.sh
│   └── stop.sh
└── app.jar
```

> When using `tar -czf ... -C "$STAGE_DIR" .`, the trailing `.` ensures the **contents** of `$STAGE_DIR` are archived, not the directory itself. Do NOT use `tar -czf ... -C "$(dirname "$STAGE_DIR")" "$APP_NAME"` — that would embed the `$APP_NAME/` wrapper directory.

## Path Relationship: artifactPath, installPath, scripts

```
On ECS after deployment:

artifactPath (/root/{app}-deploy/)       installPath (/root/{app}/)
├── scripts/  ────── copied to ──────>   ├── scripts/
│   ├── start.sh                         │   ├── start.sh
│   └── stop.sh                          │   └── stop.sh
├── app.jar                              ├── .env
└── ...                                  └── (runtime files)
       ^
       |
  tar.gz extracted here             scripts execute here:
                                    cd /root/{app} && bash scripts/start.sh
```

**Execution flow:**
1. Deployment script downloads tar.gz from OSS → extracts to `artifactPath`
2. `scripts/` directory is copied from `artifactPath` to `installPath`
3. `.env` file is written to `installPath`
4. Start/stop scripts are executed from `installPath`: `cd {installPath} && bash {applicationStart}`

> `artifactPath` and `installPath` **must** be different paths to avoid extracted artifacts overwriting runtime files.


