# Build Commands · [step-2] Compile & Package Contract

> Referenced by [step-2]. This file lists CADT-specific build constraints and the local build + upload flow.
>
> Authoritative source: [`./README.md`](README.md)

---

## 1. Local Build Commands

| lang:buildTool | Command | Artifact |
|---|---|---|
| java:maven | `mvn -DskipTests package -q` | `target/*.jar` |
| java:gradle | `./gradlew build -x test -q` | `build/libs/*.jar` |
| python:pip | `pip install build -q; python -m build --wheel` | `dist/*.whl` |
| nodejs:npm | `npm install && npm pack` | `*.tgz` |
| go:go | `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -trimpath -o "$SP" ./...` | binary |
| source:* | `COPYFILE_DISABLE=1 tar ${TAR_EXCLUDES} -czf` | `.tar.gz` |

- **Java/Maven**: Uses local Maven settings (user's `~/.m2/settings.xml`); no server-side ConfigMap override
- **Python/pip**: The `build` module may not be pre-installed — run `pip install build -q` first. The output `.whl` file (not raw `.py` source) is the artifact for §2.3 repackaging.
- **`languageVersion`**: Derived from project source code or runtime environment analysis, using full format (e.g., `"Java 11.0.27"`)
- **`source:*` skip prohibition**: If language detection identified `python`/`java`/`nodejs`/`go`, the corresponding build command above MUST be executed. Tarring raw source files without building is a critical violation — see [step-2] §2.1 anti-pattern.
- **`COPYFILE_DISABLE=1` (macOS)**: ALL `tar` commands (both `source:*` above and the §2.3 repackaging step) MUST be prefixed with `COPYFILE_DISABLE=1` on macOS. This prevents `._*` AppleDouble resource fork metadata from entering the archive.

## 2. ARTIFACT_NAME Naming (CADT Convention)

```bash
appName="${projectName}"
tag="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)"
ARTIFACT_NAME="${appName}-${tag}"
```

## 3. Artifact Upload to OSS

Use `InstallApplication`'s `filePath` mode:

```bash
cadt-deploy-on-aliyun -run InstallApplication '{"filePath":"'$ARTIFACT'","appName":"'$APP_NAME'","regionId":"'$REGION_ID'","instanceIds":"'$INSTANCE_IDS'","applicationStart":"scripts/start.sh","applicationStop":"scripts/stop.sh","artifactPath":"/root/'$APP_NAME'-deploy"}'
```

- pre-hook automatically: STS credential retrieval → OSS upload (3 retries) → size verification → injects `artifactUrl` → deploy
- **Object Key is fixed**: `{uid}/{appName}/{filename}`, **no timestamp added**; incremental updates overwrite same name
- Do not manually handle STS Token + `aliyun ossutil cp`, and do not `pip install oss2` to write custom code

## 4. Build Failure Handling

- Do not auto-fix source code / do not retry sync itself (redline 17)
- Pass complete stderr to user + give 3 fix directions (missing dependency / version mismatch / `-DskipTests`)
- **Do not enter [step-3]**
