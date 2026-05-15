# Auth and network reference

Practical details for two environmental questions the generation workflow cannot
ignore: **how the alicloud provider finds credentials** (SKILL Step 8) and
**what to do when `terraform init` can't reach the upstream registry**
(SKILL Step 6). SKILL.md references this file; it does not duplicate it.

## 1. Credential resolution chain

The alicloud provider (v1.228+) walks these seven mechanisms in order and
adopts the first one that succeeds. **SKILL never reads any credential
value** — it only checks whether each mechanism is _available_ so the user
gets an accurate diagnosis.

| # | Mechanism | Detection signal |
| --- | --- | --- |
| 1 | Static in HCL | `access_key` / `secret_key` in `provider "alicloud"` block — **SKILL Hard Rule §1 forbids emitting this**. |
| 2 | Env AK/SK | `ALIBABA_CLOUD_ACCESS_KEY_ID` + `ALIBABA_CLOUD_ACCESS_KEY_SECRET` both set. STS adds `ALIBABA_CLOUD_SECURITY_TOKEN`. |
| 3 | Shared credentials file | `~/.aliyun/config.json` exists (or `$ALIBABA_CLOUD_CREDENTIALS_FILE` points at one). `ALIBABA_CLOUD_PROFILE` selects which profile. |
| 4 | ECS instance RAM role | Running on ECS with a role attached; `$ALIBABA_CLOUD_ECS_METADATA` names the role, or HCL has `ecs_role_name = "..."`. |
| 5 | Assume RAM Role | `$ALIBABA_CLOUD_ROLE_ARN` + `$ALIBABA_CLOUD_ROLE_SESSION_NAME` set (layered on top of a base AK). |
| 6 | Assume Role with OIDC | HCL `assume_role_with_oidc { oidc_token_file = "..." }` — typical RRSA / Kubernetes ServiceAccount flow. No AK required. |
| 7 | Sidecar credentials | `$ALIBABA_CLOUD_CREDENTIALS_URI` set, or HCL `credentials_uri = "..."`. Available since provider v1.141.0. |

### Deprecated env-var names (do NOT recommend)

Provider 1.228.0 deprecated the following. If an earlier Agent output still
uses them, update the recommendation:

| Old (deprecated) | Current |
| --- | --- |
| `ALICLOUD_ACCESS_KEY` | `ALIBABA_CLOUD_ACCESS_KEY_ID` |
| `ALICLOUD_SECRET_KEY` | `ALIBABA_CLOUD_ACCESS_KEY_SECRET` |
| `ALICLOUD_SECURITY_TOKEN` | `ALIBABA_CLOUD_SECURITY_TOKEN` |
| `ALIBABACLOUD_ACCESS_KEY_ID` (no underscore) | `ALIBABA_CLOUD_ACCESS_KEY_ID` (with underscore) |
| `ALIBABACLOUD_ACCESS_KEY_SECRET` | `ALIBABA_CLOUD_ACCESS_KEY_SECRET` |

### Step 8 probe (non-reading)

Inside SKILL Step 8's pre-flight check, probe **presence** of each
mechanism without reading any value. Any one line of output = ready:

```bash
(
  [[ -n "${ALIBABA_CLOUD_ACCESS_KEY_ID:-}" ]] && [[ -n "${ALIBABA_CLOUD_ACCESS_KEY_SECRET:-}" ]] && echo "ready:env-ak-sk"
  [[ -f "$HOME/.aliyun/config.json" ]]                                                           && echo "ready:shared-config"
  { [[ -n "${ALIBABA_CLOUD_CREDENTIALS_FILE:-}" ]] && [[ -f "${ALIBABA_CLOUD_CREDENTIALS_FILE}" ]]; } && echo "ready:custom-credentials-file"
  [[ -n "${ALIBABA_CLOUD_ECS_METADATA:-}" ]]                                                      && echo "ready:ecs-ram-role"
  [[ -n "${ALIBABA_CLOUD_ROLE_ARN:-}" ]]                                                          && echo "ready:assume-role"
  [[ -n "${ALIBABA_CLOUD_CREDENTIALS_URI:-}" ]]                                                   && echo "ready:sidecar"
) | head -1
```

If no line prints → `NO_CREDENTIALS`. The error message to the user must
list **all** viable paths (not just env AK/SK) so they can pick the one
that fits their real environment — STS token, RAM role chain, or OIDC are
all legitimate and often preferred over long-lived AK.

## 2. `terraform init` network acceleration (Alibaba Cloud mirror)

Source: <https://help.aliyun.com/zh/terraform/terraform-init-acceleration-solution-configuration>

### When it's needed

`terraform init` in China-mainland networks often can't reach
`registry.terraform.io`. Signatures in the init output that indicate a
network problem (not a config problem):

- `connection refused`
- `TLS handshake timeout`
- `network is unreachable`
- `no such host`
- `context deadline exceeded` fetching `registry.terraform.io`
- any `i/o timeout` on the provider download step

### Configuration

Unlike most terraform knobs, the mirror is **not an environment variable**
— it has to be a CLI config file.

**File location** (the one Terraform reads by default):
- Linux / macOS: `~/.terraformrc`
- Windows: `%APPDATA%/terraform.rc`
- Custom: point `TF_CLI_CONFIG_FILE` at any `*.tfrc`.

**Content** (paste verbatim):

```hcl
provider_installation {
  network_mirror {
    url     = "https://mirrors.aliyun.com/terraform/"
    include = ["registry.terraform.io/aliyun/alicloud",
               "registry.terraform.io/hashicorp/alicloud"]
  }
  direct {
    exclude = ["registry.terraform.io/aliyun/alicloud",
               "registry.terraform.io/hashicorp/alicloud"]
  }
}
```

After writing the file, clear any stale state and re-init:

```bash
rm -rf <target-dir>/.terraform <target-dir>/.terraform.lock.hcl
(cd <target-dir> && terraform init -backend=false)
```

### SKILL contract: diagnose, don't write

`~/.terraformrc` is a **user-global** configuration file. SKILL's Step 6
failure branch MUST:

1. Recognize a network-class init failure from the signatures above.
2. Print the exact configuration block above and the file path.
3. Name the alternative `TF_CLI_CONFIG_FILE=<project>/.terraformrc` for
   users who prefer a project-scoped file.
4. Hand back to the user — do NOT write `~/.terraformrc` autonomously.
