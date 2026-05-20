# Cluster Connection and Access (sr-connect)

Provides cluster access for all diagnostics, debugging, and query operations in the assistant skill.

## Commands

| Command | Purpose | When to use |
|---------|---------|-------------|
| `sr-login` | Register a cluster credential locally + smoke-test connection | First time on a cluster, or to switch the password |
| `sr-logout` | Remove the local profile (no cluster-side action) | When done with a cluster |
| `sr-whoami` | Print profile state — host, user, login time, captured grants | Verify which cluster is active |
| `sr-doctor` | Diagnose connection failures (endpoint type, reachability, egress IP, /24 whitelist) | Automatically run by `sr-login` on failure; can also be called directly |
| `srsql` | Daily query entry point; classifies SQL and gates non-READ behind `--yes` | Run any SQL |

## Security model

This skill has **two layers**:

1. **FE is the authoritative permission boundary**. The user supplies their own StarRocks account; whatever they're allowed to do, they're allowed to do. The skill does **not** elevate, create, or rotate any accounts.
2. **`srsql` is a UX gate**, not a security boundary. It parses every statement with sqlglot (dialect `starrocks`) and:
   - `READ` (SELECT / SHOW / DESC / EXPLAIN / WITH / …) executes directly.
   - **Any non-READ** statement (INSERT / UPDATE / DELETE / DDL / GRANT / SET / USE / …) **is refused unless `--yes` is passed**.
   - SQL that sqlglot cannot parse falls back to a leading-keyword check; if still ambiguous, it's classified `UNKNOWN` and treated as non-READ (refused without `--yes`, executable with a soft warning when `--yes` is set).

The gate exists so the assistant doesn't *accidentally* execute writes. It is **not** a defense against a malicious caller — anyone who can run `srsql --yes` can do anything the underlying account is permitted to do.

## Local state

```
~/.starrocks/
├── {profile}.cnf       INI (MySQL client compatible) with [client] + [meta]
└── {profile}.grants    Raw SHOW GRANTS FOR CURRENT_USER() captured at login
```

- Directory mode: 700.
- File mode: 600.
- The `.cnf` is intentionally `mysql` client compatible (`mysql --defaults-extra-file=~/.starrocks/default.cnf` works), but the skill itself uses `srsql`, not the MySQL CLI.

## First-time login

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the CLI from the skill's project root
uv tool install .

# Log in (password is prompted interactively; not echoed, not logged).
# EMR Serverless internal and public endpoints both use plain MySQL wire
# protocol on port 9030 — no SSL/TLS. The same command works for either.
sr-login --host <fe-endpoint> --port 9030 --user <your-account>

# Verify
sr-whoami
srsql -e "SELECT CURRENT_VERSION()"
```

`sr-login` overwrites any existing profile of the same name silently — same semantics as `docker login` / `gh auth login`. To switch the stored password, just log in again.

## Non-interactive login (`--from-env`)

For sandbox / CI environments where the platform pre-provisions credentials, call:

```bash
sr-login --from-env
```

The CLI picks the required values up from the environment on its own. It exits with code 2 and a clear "missing" message when those values aren't present, so it's safe to call unconditionally from a setup script or from the assistant's bootstrap path — no need to inspect or echo any variable names. `--profile` is still honored if multi-cluster setup is needed.

## Multi-cluster

```bash
sr-login --profile prod    --host fe-prod.xxx    --user app_user
sr-login --profile staging --host fe-staging.xxx --user app_user

SR_PROFILE=prod    srsql -e "..."
SR_PROFILE=staging srsql -e "..."
```

## Querying

```bash
# READ — runs directly
srsql -e "SHOW FRONTENDS"
srsql -e "SELECT * FROM information_schema.backends" --format json

# Non-READ — preview first with --dry-run, then re-run with --yes
srsql --dry-run -e "INSERT INTO t VALUES (1, 2)"
srsql --yes     -e "INSERT INTO t VALUES (1, 2)"

# Multi-statement: any non-READ in the batch requires --yes for the whole batch
srsql --yes -e "USE db1; INSERT INTO t SELECT * FROM s"
```

Supported `--format` values: `tsv` (default, LLM-friendly), `json`, `table`, `markdown`, `vertical`.

## File overview

- `pyproject.toml` — declares 4 entry points: `sr-login`, `sr-logout`, `sr-whoami`, `srsql`
- `scripts/sr_connect/login.py` — sr-login flow
- `scripts/sr_connect/logout.py` — sr-logout flow
- `scripts/sr_connect/whoami.py` — sr-whoami flow
- `scripts/sr_connect/query.py` — srsql flow + multi-format output + classification gate
- `scripts/sr_connect/classify.py` — sqlglot-based SQL classifier (READ vs non-READ)
- `scripts/sr_connect/connection.py` — pymysql connection wrapper
- `scripts/sr_connect/config.py` — `~/.starrocks/{profile}.cnf` + `.grants` read/write
- `scripts/sr_connect/cli.py` — click entry points

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot connect to host:port` | Wrong endpoint type / IP not whitelisted | Read the `sr-doctor` block that `sr-login` prints right after the error (see *Connection troubleshooting* below) and follow its recommendation. |
| `Access denied for user 'X'` | Password wrong / account locked | Re-run `sr-login` to update the stored password |
| `Refusing to execute non-READ SQL without --yes` | Skill correctly classified the SQL as mutating | Confirm with the user, then re-run with `--yes` |
| `unrecognized leading keyword ...` | Statement sqlglot can't parse AND not in the keyword fallback table | Re-run with `--yes` if you're sure; or check for typos |
| `No profile 'X'` | `srsql --profile X` without prior `sr-login --profile X` | Run `sr-login` for that profile first |

## Connection troubleshooting (sr-doctor)

EMR Serverless StarRocks exposes the FE endpoint under two DNS suffixes:

| Suffix | Type | Use when |
|--------|------|----------|
| `-internal.starrocks.aliyuncs.com` | VPC internal | Client is inside the cluster's VPC (port 9030 is always open product-side) |
| `.starrocks.aliyuncs.com` | Public | Client is on the public internet; needs IP whitelist |

`sr-doctor` (`sr-doctor --host <host>` or `SR_HOST=... sr-doctor`) classifies the host, TCP-probes the port, and prints what to do next. `sr-login` runs it automatically when its own connection attempt fails — no manual step needed in that path.

### Behaviour matrix

| Endpoint | Reachable | Output |
|----------|-----------|--------|
| `*-internal.starrocks.aliyuncs.com` | yes | `[OK]` — use it directly |
| `*-internal.starrocks.aliyuncs.com` | no | Print the public swap: `export SR_HOST=<host with -internal removed>`. If the instance has not enabled its public endpoint yet, point the user to *Gateway info → Provision SLB → Public address → Enable public endpoint* (creates a billable CLB) and the doc: https://help.aliyun.com/zh/emr/emr-serverless-starrocks/manage-gateways |
| `*.starrocks.aliyuncs.com` | yes | `[OK]` — use it directly |
| `*.starrocks.aliyuncs.com` | no | Discover egress IP via `ipinfo.io`, print suggested `/24` whitelist CIDR, point to the console whitelist page. /24 buffers for NAT IP drift within a cluster. |
| Anything else | — | Fall back to generic "verify host + network path" message |

### Sample outputs

VPC endpoint unreachable:

```
[!] Cannot reach fe-c-xxx-internal.starrocks.aliyuncs.com:9030

Endpoint type: VPC (-internal.starrocks.aliyuncs.com)
Cause: Your client is not inside the cluster's VPC.

Fix: Switch to the public endpoint by removing "-internal" from the host:

    export SR_HOST=fe-c-xxx.starrocks.aliyuncs.com
    sr-login --from-env

If the instance has not enabled the public endpoint yet:
    Console -> EMR Serverless StarRocks -> instance details
    -> Gateway info -> Provision SLB  (prerequisite)
    -> Public address -> Enable public endpoint
    (creates a billable CLB; provisioning takes a few minutes)
    Docs: https://help.aliyun.com/zh/emr/emr-serverless-starrocks/manage-gateways
```

Public endpoint unreachable:

```
[!] Cannot reach fe-c-xxx.starrocks.aliyuncs.com:9030

Endpoint type: Public (.starrocks.aliyuncs.com)
Your public egress IP: 47.92.100.50
Suggested whitelist CIDR: 47.92.100.0/24
    (/24 buffers for NAT IP drift within a cluster)

Fix: Add the CIDR to the cluster whitelist:
    Console -> EMR Serverless -> instance details
    -> Network -> Whitelist -> Add CIDR -> Save

Then retry: sr-login --from-env
```

### Implementation notes

- `sr-doctor` uses standard-library `socket.create_connection` for the TCP probe (5 s timeout) and `urllib.request` for the egress IP lookup. No extra dependencies.
- Egress IP discovery uses `https://ipinfo.io/ip` (plain-text response). `api.ipify.org` and the Aliyun ECS metadata service (`100.100.100.200`) were observed to be unreliable in agenthub-style sandboxes — ipinfo.io is the only one that worked there.
- All network calls are encapsulated inside the CLI; the assistant never invokes `curl` itself, preserving the Runtime-security boundary set out in [SKILL.md](../SKILL.md#runtime-security).

## Password input guidelines

- Enter the password interactively when prompted by `sr-login`. The prompt is hidden, not echoed, and doesn't appear in `ps` or shell history.
- Do not pass `--password` on the command line — it leaks via `ps` and shell history.
