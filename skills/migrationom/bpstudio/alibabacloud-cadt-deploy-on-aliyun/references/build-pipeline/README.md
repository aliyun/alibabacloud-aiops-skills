# Build Pipeline (Local Build)

> Local build + script injection + `InstallApplication` filePath mode: the LLM runs build commands locally, injects start/stop scripts, repackages as tar.gz, then deploys via `InstallApplication` with `filePath`.
>
> `cadt-deploy-on-aliyun -run InstallApplication` with `filePath` — one command completes: pre-hook auto STS credential retrieval → OSS upload (3 retries) → size verification → injects `artifactUrl` → deploy.
>
> **Field/parameter schemas are obtained via `cadt-deploy-on-aliyun -d <Op>`; this document only covers naming pitfalls, build command matrix, script injection constraints, and deployment flow.**

## §Local Build + InstallApplication filePath Mode

> ```bash
> cadt-deploy-on-aliyun -run InstallApplication '{
>   "filePath":"/path/to/artifact.tar.gz",
>   "appName":"my-app",
>   "regionId":"cn-hangzhou",
>   "instanceIds":"i-bp1xxx",
>   "applicationStart":"scripts/start.sh",
>   "applicationStop":"scripts/stop.sh",
>   "artifactPath":"/root/my-app-deploy"
> }'
> ```

## §Build Command Matrix

| lang:buildTool | Command | Artifact |
|---|---|---|
| java:maven | `mvn -DskipTests package -q` | `target/*.jar` |
| java:gradle | `./gradlew build -x test -q` | `build/libs/*.jar` |
| python:pip | `pip install build -q; python -m build --wheel` | `dist/*.whl` |
| nodejs:npm | `npm install && npm pack` | `*.tgz` |
| go:go | `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -trimpath -o "$SP" ./...` | binary |
| source:* | `COPYFILE_DISABLE=1 tar ${TAR_EXCLUDES} -czf` | `.tar.gz` |

> **language/languageVersion/buildTool**: Derived from project source code and runtime environment analysis

## §Script Injection Requirement (InstallApplication API)

InstallApplication's API requires the artifact package to be **tar.gz** and contain `scripts/start.sh` + `scripts/stop.sh`:

| Step | Action |
|------|--------|
| 1 | Run local build command to produce artifact (.jar/.whl/.tgz/binary) |
| 2 | Inject `scripts/start.sh` + `scripts/stop.sh` (from source or standard language template; user customizes via G4 checklist in [step-3]) |
| 3 | Repackage as tar.gz with flat structure |
| 4 | `InstallApplication` with `filePath` — one command to upload + deploy |

#### start.sh Background Execution Constraint (Redline 22)

The platform side calls `bash "scripts/start.sh"` in foreground, therefore **`start.sh` itself must start the application as a daemon (`nohup <cmd> &`, `setsid`, or framework-native `--daemon`), must not block in foreground**. Running in foreground directly (e.g., `python3 app.py`, `java -jar app.jar`) will cause the deploy script to hang, get killed by Cloud Assistant after 600s timeout, and the task is marked FAILURE (see R15 in [`failure-codex.md`](../failure-codex.md)).

P27 precheck scans `start.sh` content before script injection; if no `nohup` / `&` / `setsid` / `screen -dm` / `--daemon` / `--daemonize yes` background mode is detected, blocks (see [`quality-gates.md`](../quality-gates.md) P27). Full template in [`steps/step-2-build.md`](../../steps/step-2-build.md) §2.3.1.

## §Hard Constraints

| Constraint | Impact |
|-----------|--------|
| **`.zip` format always forbidden** | Does not preserve Unix permission bits/symlinks; use `tar -czf` |
| **Single file artifacts (.jar/.whl/.tgz) not accepted by filePath** | Must repackage as tar.gz with scripts/ directory |
| **macOS must set `COPYFILE_DISABLE=1` on ALL tar commands** | Applies to both `source:*` tar (§1 matrix) AND §2.3 repackaging tar — otherwise tar writes `._*` AppleDouble resource fork metadata |
| **start.sh must use background mode** | nohup + & / setsid / screen -dm / --daemon / --daemonize yes; foreground blocking causes deploy FAILURE |
| **No absolute path `cd` in start.sh/stop.sh** | Deployment system already runs from installPath |

## Related Documentation

- State machine: [`../state-machine.md`](../state-machine.md) §`[S2]` node
- Language/tool command matrix: [`./build-commands.md`](./build-commands.md)
- Deploy modes: [`../deploy-modes.md`](../deploy-modes.md)
- Quality gates: [`../quality-gates.md`](../quality-gates.md) P27
- Failure codex: [`../failure-codex.md`](../failure-codex.md) F21-F23, R15
