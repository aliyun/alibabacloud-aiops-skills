# Aone implementation and test record

Historical snapshot dated 2026-10-18, before the subsequent push and Aone status
updates. Repository: cloud-skills-security/alibabacloud-sas-overview.
Branch: `codex/sas-requirements-fixes`; baseline: `80ef5c4`.
The scope covers reviewed requirements from Security Center and Security Center
(Situational Awareness) - Product Experience, with duplicates consolidated.
Cloud Skills Portal - Product Experience was excluded at the user's request.
This record preserves the implementation-stage evidence; it is not a live status report.

## Implemented in this repository: 13 themes, separate commits

"Complete" below means repository code, Skill documentation and offline tests were
completed. It does not establish Aone publication or acceptance against live cloud data.
Cross-Skill requirements were implemented only here; no completion is claimed for other Skills.

| Requirement / consolidated duplicates | Repository change | Separate commit | Regression tests at the time |
|---|---|---|---|
| [83995440](https://project.aone.alibaba-inc.com/v2/project/848411/req/83995440) / 83995423 | Full host pagination, stable totals, Uuid deduplication, CPU-core totals and partial results | `2e12e79` | test_pagination.py: 5 tests |
| [83703067](https://project.aone.alibaba-inc.com/v2/project/848411/req/83703067) / 83703050 | Reject missing, nonnumeric and nonfinite security scores | `e3c0bd1` | test_score.py: 4 tests |
| [85558296](https://project.aone.alibaba-inc.com/v2/project/848411/req/85558296) / 85558279; historical duplicates 83415237 / 83415208 | Consistent WAF service regions; use Hangzhou for China | `a9f4a15` | test_waf_regions.py: 3 tests |
| [85558306](https://project.aone.alibaba-inc.com/v2/project/848411/req/85558306) / 85558292 | Independent subscription, pay-as-you-go and trial detection; coexistence and module switches | `d02fed9` | test_billing.py: 4 tests |
| [85058683](https://project.aone.alibaba-inc.com/v2/project/848411/req/85058683) / 85058665 | Distinguish service opening, pay-as-you-go opening and instance expiry | `2b627c2` | test_service_times.py: 4 tests |
| [85558307](https://project.aone.alibaba-inc.com/v2/project/848411/req/85558307) / 85558293 | Require BSS permissions for bill queries; list permissions by requested scope | `3f18ae4` | test_permissions.py: 4 tests |
| [85558302](https://project.aone.alibaba-inc.com/v2/project/848411/req/85558302) / 85558290 | Capability-specific edition/activation checks and diagnostic commands at the entry point | `1e7638b` | test_prerequisites.py: 3 tests |
| [85558297](https://project.aone.alibaba-inc.com/v2/project/848411/req/85558297) / 85558283 | At most 3 CLI attempts for read queries; distinguish transient and permanent failures | `d858c0d` | test_query_errors.py: 6 tests |
| [84049992](https://project.aone.alibaba-inc.com/v2/project/848411/req/84049992) / 84049953 | Select international/China console links by account site | `389586f` | test_console_sites.py: 3 tests |
| [86050375](https://project.aone.alibaba-inc.com/v2/project/848411/req/86050375) / 86050443 / 86050355 | Chinese trigger cases, pagination/retry progress, and separate JSON/progress streams | `8b0d107` | test_progress.py: 4 tests |
| [86050367](https://project.aone.alibaba-inc.com/v2/project/848411/req/86050367) / 86050342 | CLI parameter/version checks; reject version-banner-only help | `9f58ea8` | test_cli_contract.py: 5 tests; BSS recovery evidence below |
| [84746708](https://project.aone.alibaba-inc.com/v2/project/848411/req/84746708) / 84746666 | Required inputs, same-region WAF dependencies, time units and billing cycles | `588e7a9` | test_query_parameters.py: 4 tests |
| [84746711](https://project.aone.alibaba-inc.com/v2/project/848411/req/84746711) / 84746677 | Per-item acceptance, security-response verification and overall completion status | `2599368` | test_acceptance.py: 5 tests |

## Test results and limits at the snapshot date

- `python3 -m unittest discover -s tests -v`: 54 tests passed, covering pagination boundaries, duplicate/changing/invalid responses, missing values, mixed billing, retry limits, scope, input dependencies and partial completion.
- `python3 scripts/check_cli_contract.py --help-dir /tmp/sas-cli-contracts`: all 14 API command contracts passed checks of complete help, flags, required inputs and versions. That directory held temporary local evidence and is not a repository dependency.
- The final `python3 scripts/check_cli_contract.py` run validated all 14 commands through normal `aliyun ... --help` calls (exit 0, failures={}). The first BSS startup after updating failed; a final recheck recovered, with the cause undetermined. See [cli-validation.md](cli-validation.md). This does not validate live business API data end to end.
- `git diff --check`, relative documentation links and eval JSONC structure checks passed; SKILL.md remained below 500 lines.
- No live cloud business data was requested, no paid/resource changes were made, and no Agent scenario/trigger-rate evaluation was run during that implementation stage. Added/updated eval cases had structural checks only; actual Agent behavior still required evaluation.
- At that point, changes were committed locally and had not yet been pushed or published, and Aone states had not been changed. The local BSS plugin was updated from 0.7.5 to 0.9.5 as a validation-environment change. Later push/publication actions are outside this historical snapshot.

## Seven themes whose implementation was not found in this repository

The tracked files exposed only the root SKILL.md as the business Skill entry point,
with a read-only overview workflow. They contained no implementations of the
installation, authorization, detection or remediation APIs below. Generic development
skills under `.agents` are not implementations of those business workflows.
This establishes absence from this repository, **not ownership by a specific other
repository**. The earlier categorical claim of ownership elsewhere was withdrawn.
At this stage, these themes remained unlocated; no empty commits or unrelated write
operations were added to the read-only overview.

| Requirement / duplicates | Missing implementation location and verification conditions |
|---|---|
| 85558299 / 85558286: CloudAssistantStatus string handling | DescribeCloudAssistantStatus consumer in the installation flow; test string true/false/unknown |
| 83415238: Verify authorization after installation | Post-installation asset authorization check; distinguish Agent online status from effective authorization |
| 83415234: Authorization binding delay, naming and errors | BindAuthToMachine caller and server-state contract; observed delay must not become an asserted SLA |
| 83415235 / 83415201 + 83415252 / 83415224: Upload API selection and naming | Actual upload call chain and backend interfaces; do not switch CreateFileDetectUploadUrl / CreateBatchUploadUrl without evidence |
| 83415231 / 83415200: Required file-detection inputs | CreateFileDetect argument construction; validate HashKey/OssKey/DownloadUrl combinations by type |
| 83415239 / 83415219: Exact vulnerability-name matching | DescribeUuidsByVulNames caller; exact-name lookup and disambiguation of multiple candidates |
| 83415248: Alert-remediation acceptance | HandleSecurityEvents and remediation-state polling; TaskId means accepted, not completed |

## Previously published/rejected items: reviewed without duplicate changes

The following states were read during planning; that review did not update Aone:

| Requirement / duplicates | Handling |
|---|---|
| 83415249 / 83415223: CLI installation instructions | Published; actual commands were checked under the CLI consistency work, without a duplicate commit |
| 83415236: Invalid event UUID | Published; the historical server-side fix was not reimplemented here |
| 83415251 / 83415229: All vulnerability types | Rejected; the read-only overview was not expanded into vulnerability remediation |
| 83415226 / 83415197: API naming | Rejected; current overview APIs were checked individually, without introducing DescribeVulList absent a corresponding scenario |
