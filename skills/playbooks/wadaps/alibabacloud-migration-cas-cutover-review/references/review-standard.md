# alibabacloud-migration-cas-cutover-review Review Standard

> Review-rule reference: the ATA cloud-migration cutover best-practice series + "Dissecting Cloud Migration - Cutover Plan Review Guide"

## 0. Core 5-Dimension Review (added in v4.0, highest priority)

The following 5 dimensions apply to all cutover scenarios (batch / full / other) and are the first-priority checks of cutover-plan review. Missing any dimension produces a HIGH or CRITICAL issue.

| # | Dimension | Check logic | Risk description | Severity |
|---|------|----------|----------|--------|
| 1 | Maintenance notice | Whether the manual configures a maintenance / outage notice | If not configured, users have no awareness, which may cause complaints and business disputes | HIGH |
| 2 | Traffic-switching method | Whether a blocking layer is configured (Nginx interception / gateway interception), rather than relying only on a DNS switch | With DNS switch only, carrier Local DNS caching makes the effective time uncontrollable (TTL usually 10min~24h), and some user traffic still hits the source | CRITICAL |
| 3 | Source-database read-only | Whether the database is set to read-only + whether sessions are killed | Only stopping the app without read-only → other entries (scheduled jobs / direct connect) may still write to the source, causing incremental-sync failure or data inconsistency; read-only set but no kill session → long-connection transactions still hold write locks | CRITICAL |
| 4 | Alibaba Cloud application restart | Whether an application-restart step is included after the cutover completes | No restart → after the database restores read-write, old connections in the application connection pool may fail to reconnect automatically, causing business exceptions; when restarting, note startup order and dependencies, and a two-phase startup is recommended (verify with a single Pod first, then batch scale-out) | HIGH |
| 5 | Rollback decision conditions | Whether structured rollback decision conditions are defined (decision point, decision maker, quantified metric) | No rollback decision conditions → hesitation when problems occur on cutover day, missing the best rollback window; two decision points are recommended: before / after traffic forwarding; rollback is generally not done after a DNS switch | CRITICAL |

### Detailed Check Points for Each Dimension

**Dimension 1: Maintenance notice**
- Keywords: outage notice, maintenance notice, cutover notice, maintenance page, maintenance, outage notification
- Check: whether the manual has a notice-configuration step (including mount location: source Nginx / mini-program / APP popup)
- Suggestion when missing: recommend configuring a maintenance notice before the cutover, informing users of the maintenance time window and recovery expectation

**Dimension 2: Traffic-switching method**
- Keywords: blocking layer, Nginx interception, gateway interception, traffic interception, maintenance page, 503, blocking verification
- Check: whether there is a blocking-layer configuration (Nginx return 503 / gateway maintenance page / WAF interception rule), rather than only a DNS change
- DNS-only warning: DNS effectiveness is affected by carrier TTL caching and is uncontrollable; recommend adding an Nginx/gateway-layer interception as the blocking layer
- With a blocking layer: check whether a blocking-verification step is included (verify interception takes effect in advance)

**Dimension 3: Source-database read-only**
- Keywords: read-only, read_only, read only, super_read_only, kill session, kill processlist, set global
- Check logic (conditional branch):
  - No read-only + no kill session → CRITICAL: only stopping the app cannot prevent other entries from writing
  - Read-only + no kill session → HIGH: long connections / uncommitted transactions may still write, sessions must be killed to clean up
  - Read-only + kill session → PASS
- Note: read-only should be set at the account level (not instance level), avoiding impact on the DTS incremental-sync link

**Dimension 4: Alibaba Cloud application restart**
- Keywords: restart, rolling restart, kubectl rollout, systemctl restart, startup order, two-phase
- Check logic (conditional branch):
  - No restart step → HIGH: after the database restores read-write, old connections in the application connection pool may fail to reconnect automatically
  - Restart but no startup-order description → MEDIUM: recommend clarifying startup order (base services first) and two-phase strategy
  - Restart + startup order → PASS

**Dimension 5: Rollback decision conditions**
- Keywords: rollback decision, rollback condition, rollback trigger, decision maker, rollback window, rollback time point, decision point
- Check: whether there is a definition of rollback decision conditions independent of operation steps (including decision maker, quantified metric, decision time point)
- Suggestion when missing: recommend designing structured rollback decisions — set two key decision points (before / after traffic forwarding), clarify the decision maker and quantified trigger conditions; rollback is generally not done after a DNS switch
- Has rollback steps but no decision conditions → HIGH: has rollback operations but lacks the "when to roll back" judgment criteria

---

## 1. ATA Standard 6 Major Check-Item Categories

| Category | Weight | Check points |
|------|------|----------|
| Business research and assessment | 15% | business dependencies, upstream/downstream systems, business peaks, continuity requirements |
| Cutover plan design and verification | 20% | plan review, rehearsal verification, script preparation, rollback plan |
| Environment and resource preparation | 15% | resource configuration, network connectivity, security groups, SSL certificates |
| Data migration and synchronization | 25% | full migration, incremental sync, consistency check, reverse sync |
| Monitoring and contingency preparation | 15% | monitoring dashboard, alert thresholds, contingency plan, contacts |
| Organizational assurance and communication mechanism | 10% | staffing formation, communication mechanism, escalation process, customer liaison |

## 2. Key Nodes of the Cutover Process

Database read-only setting → incremental-sync link status check → application stop (stop source writes) → final data-consistency check → gray-release strategy (ratio, observation time, rollback conditions) → rollback decision conditions (quantified metrics) → business verification cases → ops handover.

## 3. The 6 Key Elements of a Rollback Plan

1. Reverse-sync link (Alibaba Cloud → source)
2. Rollback trigger conditions (quantified metrics)
3. Rollback decision process (decision maker, decision mechanism)
4. Data-consistency assurance (no loss, no duplication)
5. Rollback verification steps (how to confirm success)
6. Rollback time window (maximum time control)

## 4. Cutover Readiness Scorecard (out of 100)

| Dimension | Weight | Scoring method |
|------|------|----------|
| CheckList completeness | 20% | coverage of the 6 major categories + key check items + accountability |
| Cutover process standardization | 25% | key-node coverage + time-fill rate + step order |
| Rollback plan feasibility | 25% | completeness of the 6 elements + reverse sync + accountability |
| Resource-configuration sufficiency | 15% | dynamic analysis based on content |
| Monitoring & contingency preparation | 10% | dynamic analysis based on content |
| Organizational-assurance effectiveness | 5%  | owner/time fill situation |

Risk levels:

| Overall score | Risk level | Recommendation |
|----------|----------|------|
| 90-100 | Low risk | Cutover can be executed |
| 70-89  | Medium risk | Recommend supplementing before execution |
| 50-69  | High risk | Must remediate and re-review |
| 0-49   | Very high risk | Not recommended to execute the cutover per this plan |

## 5. The 18 Review Focus Points of Batch Cutover

### Database read-only and session management
1. The source database must kill sessions when restoring read-write
2. Database read-only cannot be an instance-level operation (account level, not affecting DTS)
3. Redis read-only limitation (6.0+ version, passwordless-scenario handling)
4. ElasticSearch cannot be set read-only (whitelist scheme and data consistency)
5. Risk of Alibaba Cloud database being written dirty (set read-only in advance)
6. The Alibaba Cloud database must kill sessions when restoring read-write
7. Application status check after the Alibaba Cloud database restores read-write (auto-reconnect)

### Pre-checks
8. Pre-check: cross-cloud access latency and bandwidth check

### Reverse sync
9. No reverse sync must be flagged in red (meeting-minutes traceability)
10. Reverse-sync link pre-check (created and pre-check passed but not started)

### Message middleware and scheduled jobs (added in v3.3)
11. Kafka/message-middleware consumption confirmation — stopping traffic does not equal stopping consumption; confirm whether passive message sources such as scheduled jobs still produce messages; different message types need separate handling
12. Scheduled-job stop method and time cost — confirm the specific stop method (one-by-one / batch / API), and estimate the time accordingly (empirical value: clicking hundreds of scheduled jobs one by one takes about 30 minutes)

### Target-side state and service management (added in v3.3)
13. Target-side initial-state pre-statement — Alibaba Cloud MySQL/Redis initial read-only status, whitelist-setting risks, and the initial state of applications and scheduled jobs must be explicitly recorded
14. Service restart strategy — confirm the total number of services, startup order (base services first), and a two-phase startup is recommended (verify with a single Pod first, then batch scale-out), avoiding dependent-service startup failures

### Document standards and process consistency (added in v3.3)
15. Estimated time cost for cutover steps — each operation step must add an estimated-time-cost field for deviation analysis on cutover day
16. Nginx/proxy-layer config-change standard — must include the full flow: write config in advance → back up current config → overwrite with new config → reload; the backup action must be reflected in the document
17. Big-data consumption-link cutover — when an independent big-data Kafka consumption is involved, confirm the Flink job stop method, check message backlog during the recovery phase, and recommend synchronizing messages and switching consumers in advance
18. Process-consistency check — stop/recover steps must correspond one-to-one, and the DNS switch timing should be before external traffic is recovered

## 6. The 6 Review Focus Points of Full Cutover

1. Maintenance-notice check (mounted on source / target / mini-program, clarify details)
2. Refer to the batch-cutover review points (items 1-18)
3. Blocking-layer check (DNS effectiveness time uncontrollable, Local DNS hijacking)
4. Blocking-layer verification check (verify the blocking function in advance)
5. Maintenance-notice mounting method and traffic interception (added in v3.3) — WeChat mini-program auto-interception vs Alipay no interception vs Nginx mounting; the method and deployment location must be clarified
6. Structured rollback decision conditions (added in v3.3) — independent of operation steps, set two key decision points (before / after traffic forwarding); rollback is generally not done after a DNS switch

## 7. The 10 Sections of the Report Output

1. **Overview**: Sheet-page findings, per-dimension scores
2. **CheckList completeness analysis**: missing categories, key check items, accountability
3. **Cutover process standardization analysis**: missing nodes, step order, rollback decision points
4. **Rollback plan feasibility analysis**: check of the 6 key elements, fatal defects
5. **Data migration analysis**: coverage of the 8 elements
6. **Cutover scenario-specific check**: execute scenario-specific checks and scoring by scenario type
7. **Domain-list analysis**: completeness check
8. **Issue-list summary**: classified by severity
9. **Remediation recommendations**: P0 immediate-action list + suggested supplementary documents
10. **Summary**: scenario type, overall assessment, core issues, next-step recommendations
