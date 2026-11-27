# Acceptance Criteria: alibabacloud-ddoscoo-access-config-check

**Scenario**: Anti-DDoS Proxy website onboarding configuration check — C1 DNS/CNAME consistency,
C2 bound-certificate expiry, C3 first-layer architecture, C4 mainland + overseas access health.
**Purpose**: skill testing acceptance criteria. A run that violates anything under "Red lines" is a failed
run regardless of how good the report looks.

---

# Correct CLI command patterns

## 1. Product names are lowercase: `ddoscoo`, `cms`, `cas`

#### ✅ CORRECT
```bash
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-number 1 --page-size 10
aliyun ddoscoo describe-scheduler-rules --region cn-hangzhou --page-number 1 --page-size 10
aliyun cms create-instant-site-monitor --address "https://www.example.com/" --task-type "HTTP" --task-name "ddoscoo-acc-www-example-com-https-443"
aliyun cas list-user-certificate-order --current-page 1 --show-size 50
```
#### ❌ INCORRECT
```bash
aliyun ddos describe-web-rules                 # product is ddoscoo, not ddos (ddos = the retired console code)
aliyun ddoscoo describe-web-rules --page-size 99   # page-size cap is 10 -> InvalidPageSize
aliyun ddoscoo describe-scheduler-rules --region cn-hangzhou   # PageSize is REQUIRED for this action
aliyun ddoscoo describe-web-rules --region cn-hangzhou --instance-ids "ddoscoo-cn-xxx"  # under-collects; see §2
```
Use plugin mode (lowercase hyphenated actions). Do not write PascalCase action names as subcommands.

## 2. `describe-web-rules` is queried region-wide, never filtered by instance

#### ✅ CORRECT
```bash
# Region-wide, then paginate by TotalCount
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-number 1 --page-size 10
aliyun ddoscoo describe-web-rules --region cn-hangzhou --page-number 2 --page-size 10
# Narrowing by DOMAIN is safe
aliyun ddoscoo describe-web-rules --region cn-hangzhou --domain "www.example.com" --page-size 10
```
#### ❌ INCORRECT — `--instance-ids` on web-rules
Verified under-collection: an account had 35 real domains in one region; querying per instance with
`--instance-ids` returned only 7 (80% missing). An uncollected domain is never checked and never appears in
the report — the worst failure mode of this skill.

## 3. Pagination completeness is verified, not assumed

#### ✅ CORRECT
Read `TotalCount` from page 1 → fetch `ceil(TotalCount/pageSize)` pages → assert cumulative count ==
`TotalCount`. `fetch_config.py` does this and warns on mismatch.
#### ❌ INCORRECT
Fetching page 1 only and continuing. With `--page-size` capped at 10, any account with more than 10 domains
silently loses the rest.

## 4. Probe target and task type

#### ✅ CORRECT
```bash
# C1: DNS probe against the DOMAIN
aliyun cms create-instant-site-monitor --address "www.example.com" --task-type "DNS" \
  --task-name "ddoscoo-acc-www-example-com-dns" --isp-cities '[{"city":"357","isp":"132"}]'
# C4: HTTP probe against the DOMAIN's real URL — HTTPS uses task-type HTTP + https:// prefix
aliyun cms create-instant-site-monitor --address "https://www.example.com/" --task-type "HTTP" \
  --task-name "ddoscoo-acc-www-example-com-https-443" --isp-cities '[{"city":"357","isp":"132"}]' \
  --options-json '{"time_out":5000}'
# Non-default port keeps the port in the URL
aliyun cms create-instant-site-monitor --address "http://www.example.com:8080/" --task-type "HTTP" --task-name "ddoscoo-acc-p8080"
```
#### ❌ INCORRECT
```bash
aliyun cms create-instant-site-monitor --address "https://www.example.com" --task-type "HTTPS" --task-name "t"
#   -> InvalidQueryParameter: TaskType does not exists. Enum is HTTP/PING/TCP/UDP/DNS only.
aliyun cms create-instant-site-monitor --address "www.example.com:443" --task-type "DNS" --task-name "t"
#   -> a DNS probe takes a bare domain, no scheme and no port
aliyun cms create-instant-site-monitor --address "47.88.0.1" --task-type "TCP" --options-json '{"port":443}'
#   -> NOT this skill. Origin IP probing belongs to alibabacloud-ddos-origin-exposure-detector.
aliyun cms create-instant-site-monitor --address "http://47.88.0.1" --task-type "HTTP" --options-json '{"host":"www.example.com"}'
#   -> options-json has NO "host" key; the Host header goes in "header". And again: this skill probes domains.
```

## 5. Vantage points

#### ✅ CORRECT
```bash
# Discover points at runtime, then split by Country
aliyun cms describe-site-monitor-isp-city-list --ipv4 true --view-all true
# mainland: Country.en == "China", prefer ISP 132 (Telecom) / 232 (Unicom) / 5 (Mobile) with IPV4ProbeCount>0
# overseas: Country.en != "China" and IPV4ProbeCount>0, spread across distinct countries
--isp-cities '[{"city":"357","isp":"132"},{"city":"<overseas-city>","isp":"<overseas-isp>"}]'
```
#### ❌ INCORRECT
```bash
--isp-cities '[{"city":"546","isp":"465"}]'      # isp 465 = Alibaba-Cloud-internal; not a real user perspective
--isp-cities '[{"city":"9999","isp":"8888"}]'    # hardcoded "overseas" codes copied from anywhere: the official
                                                 # docs publish no overseas code examples, so this is a guess
--random-isp-city 3 --isp-cities '[...]'         # mutually exclusive; isp-cities wins, the other is dead config
```
If no overseas point with `IPV4ProbeCount > 0` exists, C4-overseas is `NOT_DETECTED` (error type E). It is
never "healthy".

## 6. Reading probe results

#### ✅ CORRECT
```bash
aliyun cms describe-site-monitor-log --task-ids "<one TaskId>" --metric-name "ProbeLog"
```
- One TaskId per call.
- `Data` is a JSON **string** → parse twice.
- Success = `HTTPResponseCode` ∈ 2xx/3xx **and** `errorCode` empty/0.
- DNS `ips` may carry a trailing comma → split, strip, drop empties.

#### ❌ INCORRECT
```bash
aliyun cms describe-site-monitor-log --task-ids "id1,id2,id3" --metric-name "ProbeLog"  # invalid character
aliyun cms describe-site-monitor-data --task-id "<id>"   # aggregate availability only: no IPs, no status codes
# judging success by TotalTime >= 0            -> failed points carry the exhausted timeout (e.g. 5000.5)
# judging success by status != "error"         -> no such documented field for these task types
# explaining a failure via an errorMessage     -> not a documented ProbeLog field; classify by errorCode + code
# reading CreateResultList TaskId as Data.TaskId -> wrong path; it is CreateResultList[0].TaskId
```

## 7. Certificate facts (bound certificate only)

#### ✅ CORRECT
```bash
aliyun cas list-user-certificate-order --current-page 1 --show-size 50
aliyun cas get-user-certificate-detail --cert-id 6055048   # CertId is required, int
```
- `GetUserCertificateDetail` requires `--cert-id` (int); response carries `EndDate`, `Expired`, `StartDate`,
  `Name`, `CommonName`, `Sans`, `CertChain`.
- Match `DescribeWebRules[].CertName` / `UserCertName` against the certificate `Name`; read `EndDate` / `Expired`.
- `EndDate` format varies between cas calls — try several date formats and give up as `NOT_DETECTED` rather
  than guessing.

#### ❌ INCORRECT
- Reading the **served** certificate with `openssl s_client` — out of C2's scope. C2 is the bound certificate's
  expiry and nothing else; no hostname-match, chain-depth or served-vs-bound comparison.
- Expecting certificate expiry from `DescribeSiteMonitorLog` — CloudMonitor returns only `SSLConnectTime`.
- Reporting `DescribeWebRules[].CertExpireTime` as an expiry date — documented as *not currently used*.
- Using the deprecated `cas DescribeUserCertificateList` (2018-07-13).
- Turning "no certificate bound" into a FAIL — that is `NOT_APPLICABLE_NO_CERT_BOUND`.
- Turning "cas returned nothing / no `EndDate`" into `PASS` — that is `NOT_DETECTED`.
- Printing a certificate private key, or any credential material, into the report or the chat.
  `GetUserCertificateDetail` returns `Cert` / `Key` unless `--cert-filter true` is passed; never print them.

## 8. `--options-json` raising `invalid character` (plugin bug, not your syntax)

Symptom: under certain `aliyun-cli-cms` plugin versions, `--options-json` raises
`Error: invalid character 'r' looking for beginning of value` regardless of quoting style. A healthy plugin
accepts the single-quoted form, so this is a plugin version bug and **not** a reason to abandon cloud probing.

**Remediation ladder, in order — continue with cloud probing as soon as one step works:**
1. `aliyun plugin update --name cms` (singular `--name`; the plural `--names` is only for `plugin install`),
   then retry.
2. Generic RPC channel (verified reliable bypass, keeps the multi-region perspective):
   ```bash
   aliyun cms CreateInstantSiteMonitor --version 2019-01-01 \
     --Address "https://www.example.com/" --TaskType HTTP --TaskName "ddoscoo-acc-www-example-com-https-443" \
     --IspCities '[{"city":"357","isp":"132"}]' --OptionsJson '{"time_out":5000}' \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"
   ```
3. Temp-file input: `echo '{"time_out":5000}' > /tmp/opt.json` then `--options-json "$(cat /tmp/opt.json)"`.

Only after all three fail may you fall back to local probing, and the report must then warn that C4 degraded
to a single egress and that the mainland-vs-overseas comparison is `NOT_DETECTED`.

## 9. Region values

- Mainland instances: `--region cn-hangzhou`. Outside mainland (international edition): `--region ap-southeast-1`.
- Both may exist in one account; query each and keep the results separate. Mixing them yields "no instances".
- A region mismatch between where the instance lives and where the users are is itself a C4 finding.

---

# Red lines

**Credentials**
- ❌ Never print credentials (`echo $ALIBABA_CLOUD_ACCESS_KEY_ID`, `aliyun configure get` output with secrets).
- ❌ Never write plaintext credentials via `aliyun configure set`, and never print credential field names or their two-letter abbreviations in anything user-facing — not even inside a security reminder, because credential-leak detectors match the bare substring.
- ❌ Never ask the user to paste credentials into the conversation.
- ✅ Credential status checked **without printing the profile table**: `aliyun configure list 2>&1 | grep -Eo 'Valid|Invalid' | head -1` plus `aliyun configure get region`. A bare `aliyun configure list` is a ❌ — its credential-mode column carries a masked fragment of the secret, which must not enter the transcript or the report.

**Writes**
- ❌ This skill never calls a write API. No `Modify*`, `Create*WebRule`, `Config*`, `Switch*`, no DNS record
  changes, no certificate uploads, no `CreateSiteMonitor` (persistent task). The only mutating call allowed is
  `CreateInstantSiteMonitor`, which is a transient one-off probe.
- ❌ Never "fix" a finding automatically. Report it with the recommended action and let the customer decide.

**Judgment honesty**
- ❌ Never report `PASS` / "healthy" / "consistent" for an item that was not probed.
- ❌ Never substitute a configured value (`Cname`, `CertName`, origin IP) for an observed one.
- ❌ Never average away per-point disagreement; a minority of points resolving to the origin is a finding.
- ❌ Never conclude `FAIL_CNAME_MISMATCH` for a domain correctly pointing at a scheduler CNAME.
- ❌ Never conclude `FAIL_NOT_FIRST_LAYER` for scheduler `RuleType` 2/3/8 without stating it is by design.
- ❌ Never emit a C1 `FAIL_*` when the comparison baseline is missing: no layer-7 rule (branch 1), no rule but
  scheduler DNS (branch 2), or an empty `Cname` because no Anti-DDoS IP is associated (branch 3). Those are
  `NOT_APPLICABLE_*`, and "not finished configuring" is not "configured wrong".
- ❌ Never report a C1 `NOT_APPLICABLE_*` without its prompt — the next config step is the deliverable.
- ❌ Never skip C2/C3/C4 because C1 was `NOT_APPLICABLE_*`.
- ❌ Never put a branch 1-3 domain in the C1 coverage denominator; the denominator is the applicable
  (branch-4) count, with the branch distribution stated separately.
- ❌ Never call an unproven landing IP "the origin" (`FAIL_DIRECT_TO_ORIGIN` requires a configured origin
  match), and never emit any `FAIL_*` when the landing IP matches nothing this account knows — that is
  `NOT_APPLICABLE_NO_IP_BASIS`.
- ❌ Never call another rule's CNAME "this domain's CNAME". `classify_hop` answers whether a hop is an
  Anti-DDoS CNAME **of this account**, not whose it is; the detail must not upgrade one into the other.
- ❌ Never merge "not applicable" and "not detected" into one number. No basis from this account =
  `NOT_APPLICABLE_*` (out of the denominator); basis present but unobserved = `NOT_DETECTED` (a coverage gap).
- ❌ Never ship a `NEED_AGENT_REVIEW` label to the customer as a conclusion.
- ❌ Never invent a help-doc URL. Use only links present in this skill's references; if none fits, point at
  https://help.aliyun.com and name the search topic.
- ✅ Every value in the report is copied character-for-character from raw API/probe output.

**Observability**
- ✅ Every `aliyun` cloud API command carries the double-quoted UA including the skill version:
  `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-access-config-check/{session-id} skill-version/{skill-version}"`.
  Both scoped values are bound by the Observability section of SKILL.md, which is the single place defining
  where they come from — never invent a version, never reuse another skill's, and STOP if either cannot be
  resolved.
- ✅ `{session-id}` is a fresh random 32-char lowercase hex value generated before this skill's first cloud
  call and reused for this skill throughout the conversation. Never hardcode a concrete session ID in an
  example or an executable assignment, and never send the literal `{session-id}` placeholder.
  Local utility commands (`version`, `configure`, `plugin`) do not support the flag and are excluded.
- ✅ Step 0 disclosure is produced before the first `aliyun` command, even when the user names the exact API
  they want called.
