# Acceptance Criteria: ddos-origin-exposure-detector

**Scenario**: Anti-DDoS Proxy origin-server cloud IP exposure risk detection
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — the product name must be `ddoscoo` and `cms` (lowercase)

#### ✅ CORRECT
```bash
aliyun ddoscoo describe-web-rules --region cn-hangzhou
aliyun cms create-instant-site-monitor --address "www.example.com" --task-type "DNS" --task-name "t1"
```
#### ❌ INCORRECT
```bash
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-size 99   # Error: page-size cap is 10 (raises InvalidPageSize)
aliyun ddos describe-web-rules           # Error: the product name should be ddoscoo, not ddos
```
- Do NOT use traditional API-name form (PascalCase subcommand, e.g. `describe-web-rules` written as its PascalCase API name). Always use plugin mode: lowercase words joined by hyphens (`describe-web-rules`, `create-instant-site-monitor`).

## 2. Command — the action must exist under the product

- `ddoscoo describe-web-rules` ✅ (DescribeWebRules)
- `ddoscoo describe-domains` ✅ (DescribeDomains)
- `cms create-instant-site-monitor` ✅ (CreateInstantSiteMonitor)
- `cms describe-site-monitor-log` ✅ (DescribeSiteMonitorLog)

## 3. Parameters — parameter names must match the API definition

#### ✅ CORRECT
```bash
# create-instant-site-monitor HTTP probe: bind the Host header via the header field of options-json (no host key)
aliyun cms create-instant-site-monitor \
  --address "http://1.2.3.4:443" \
  --task-type "HTTP" \
  --task-name "probe1" \
  --options-json '{"header":"Host: www.example.com","time_out":5000}'
# TCP/UDP probe: address holds only the IP; the port goes into the port field of options-json
aliyun cms create-instant-site-monitor \
  --address "1.2.3.4" \
  --task-type "TCP" \
  --task-name "probe2" \
  --options-json '{"port":443,"time_out":5000}'
```
- `TaskType` valid enum values: `HTTP` / `PING` / `TCP` / `UDP` / `DNS`
- `AgentGroup` valid enum values: `PC` / `MOBILE`
- `metric-name` (describe-site-monitor-log) valid value: `ProbeLog` (currently the only one)
- **HTTP options-json has no `host` key**; the Host header is written in the `header` field: `"header":"Host: <domain>"`
- **The `--address` for TCP/UDP must not include a port** (`ip:port` will raise `illegal port`); specify the port via `--options-json '{"port":N}'`

#### ❌ INCORRECT
```bash
aliyun cms create-instant-site-monitor --address "1.2.3.4" --task-type "PROBE"  # TaskType not in the enum
aliyun cms create-instant-site-monitor --url "..." --type "HTTP"               # wrong parameter names
aliyun cms create-instant-site-monitor --address "1.2.3.4:443" --task-type "TCP" --task-name "p"  # TCP address must not include a port
aliyun cms create-instant-site-monitor --address "http://1.2.3.4" --task-type "HTTP" --options-json '{"host":"x"}'  # HTTP has no host key, the Host header is ineffective
```

## 4. Region values

- Anti-DDoS instances in the Chinese mainland: `--region cn-hangzhou` ✅
- Anti-DDoS instances outside the Chinese mainland: `--region ap-southeast-1` ✅
- Mixing them will result in no instance data being found ❌

## 5. In the D scenario, HTTP probes must carry a Host header (via the header field)

#### ✅ CORRECT
```bash
--options-json '{"header":"Host: www.example.com","time_out":5000}'
```
#### ❌ INCORRECT — using the host key: the Host header will not be bound, and an origin that routes by Host will misjudge
```bash
# Missing the header field's Host: ...; options-json has no host key
aliyun cms create-instant-site-monitor --address "http://1.2.3.4:443" --task-type "HTTP" --task-name "p" --options-json '{"host":"www.example.com"}'
```

# 6. Correct handling of `--options-json` raising `invalid character` (a plugin bug, not a syntax error)

Symptom: under certain versions of the `aliyun-cli-cms` plugin (such as 0.7.2), `--options-json` raises
`Error: invalid character 'r' looking for beginning of value` regardless of single quotes / double quotes / file://. Verified: under a healthy plugin, this Skill's single-quote form submits normally (reaching the authentication/business response), so **this is a plugin version bug, not a JSON syntax error, and not a reason to immediately fall back to local probing**.

#### ✅ CORRECT — first remediate cloud site monitoring, and only fall back as a last resort
```bash
# 1) Retry after updating the plugin (plugin update only supports the singular --name; the plural --names is only supported by plugin install)
aliyun plugin update --name cms
# 3) Pass the argument via a temporary file, still in plugin mode
echo '{"port":443,"time_out":5000}' > /tmp/opt.json
aliyun cms create-instant-site-monitor --address "1.2.3.4" --task-type "TCP" --task-name "probe" --options-json "$(cat /tmp/opt.json)"
```

Step 2 — generic RPC channel (fallback bypass for the plugin parser): if the plugin subcommand parser itself is broken, the same `CreateInstantSiteMonitor` API can be invoked through the Alibaba Cloud generic OpenAPI (RPC) channel with `--version 2019-01-01` and PascalCase parameters (`--TaskType TCP`, `--TaskName probe`, `--Address "1.2.3.4"`, `--RandomIspCity 3`, `--OptionsJson '{"port":443,"time_out":5000}'`), plus the `--user-agent` flag. Prefer plugin mode (step 1/3); use the generic-RPC channel only as a bypass when the plugin parser is confirmed broken, because it preserves the full multi-location cloud-probe perspective.

#### ❌ INCORRECT
```text
# On seeing invalid character, directly conclude "cloud site monitoring is unavailable" and fully fall back to local probing,
# causing all IPv6 origins to be missed and losing the multi-location perspective —— falling back without first executing the remediation gradient = unacceptable
```
- Only if all three remediation steps fail may you fall back to local, and the report must explicitly warn: this S2 run degraded to local single-egress probing; it is recommended to fix the plugin and rerun cloud site monitoring.
- **IPv6 origins are an independent limitation (unrelated to the plugin bug)**: the probing end of cloud site monitoring `CreateInstantSiteMonitor` is forced to use the IPv4 stack, and **does not support IPv6 target probing at all** (in tests, specifying `IPV6ProbeCount>0` probe points to probe a known-reachable IPv6 still raises `dial tcp4: no suitable address found`); even with a healthy plugin and an available generalized RPC channel, IPv6 cannot be probed. IPv6 origins can only fall back to local `nc -6`; when there is no IPv6 egress, mark it directly as "not detected" and it must not be described as "not exposed".

# Security Red Lines

- ❌ Do not print credentials with commands like `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`
- ❌ Do not write plaintext AK/SK via `aliyun configure set`
- ✅ Only use `aliyun configure list` to check credential status
- ✅ Every `aliyun` cloud API command must carry `--user-agent AlibabaCloud-Agent-Skills/ddos-origin-exposure-detector/{session-id}` (observability convention)
