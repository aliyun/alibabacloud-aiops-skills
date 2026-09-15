# Lifecycle Runtime Playbook

Attribution playbook for "the lifecycle rule does not take effect".
Every mechanism below is grounded in the official documentation
(source: help.aliyun.com, "Lifecycle rules based on last modified
time" - original Chinese doc title translated,
fetched 2026-08-27) and measured ticket root causes. Use it as a
decision tree: verify the configuration first (the entry script does
this), then walk the timing / matching / conflict branches.

## 1. Execution mechanism (timing basis)

- **Loading window**: after a rule is created, OSS loads it within
  **24 hours**. A rule created today cannot act today. The console
  status stays at the "loading/starting" label as the normal loaded
  state and never flips to "enabled" in some console views.
- **Daily run**: execution always starts at **08:00 Beijing time**
  every day. There is no on-demand execution.
- **Days-policy spacing**: for a Days=N policy, the gap between the
  object's last-modified time and the 08:00 run must exceed 24 hours.
  An object uploaded after 08:00 today is first eligible at the
  08:00 run TWO days later (measured example: Days=1, upload
  2020-07-20 08:00+ -> deletion starts 2020-07-22 08:00).
- **Large-scale lag**: a single daily run normally finishes within
  24 hours for <=10^9 objects in the major CN regions (<=10^8 in other
  regions); very large buckets / many tags / many historical versions
  can stretch the run to days or weeks. Each historical version counts
  as one operation.
- **Update caution**: updating a rule can abort the same day's task;
  never recommend frequent rule edits as a "refresh".
- **Time basis**: lifecycle evaluates the object's **last modified
  time** (the last-access-time strategy exists only when
  access-tracking based rules are enabled for the bucket). A
  lifecycle conversion does NOT refresh the last-modified time - a
  later rule still judges by the original timestamp (ticket root
  cause: users assumed conversion updates the timestamp and got still-
  needed files moved to Cold Archive).
- **Access-time based rules** (when enabled, source: help.aliyun.com
  "Lifecycle rules based on last access time"): may only TRANSITION
  data - they can NEVER delete. `LastAccessTime` updates are
  asynchronous (usually within 24 hours; only the FIRST access within
  a 24-hour window is recorded) and are initialized to the moment
  access tracking was enabled for the bucket. Standard->IA rules may
  optionally auto-convert BACK to Standard when the object is
  accessed again (this is the only upward automatic path and the
  lowest priority action in the official priority ladder). Converting
  Standard/IA -> Archive/ColdArchive/DeepColdArchive by access-time
  rules requires a support-ticket whitelist.
- **Regionless buckets**: a bucket without a region attribute only
  stores Standard objects, so lifecycle runs DELETION actions only
  there (no transitions); access-time based rules are unsupported on
  regionless buckets and in finance-cloud regions.

## 2. Matching conditions (why a rule skips an object)

- **Prefix matching is literal**: no wildcards, no suffix matching, no
  regex, no dynamic variables. `img` matches `imgtest.png`; `img/`
  matches only keys under `img/`. A prefix must be the FULL path
  (`src/dir1`, not `dir1`) and may not start with `/` or `\`.
  A rule configured for the entire bucket (empty prefix) is treated
  as having prefix overlap with every other rule - plan accordingly.
- **Invisible-character footgun** (measured ticket root cause, oss07
  ticket 0002HRH86X): a prefix copy-pasted from the console may carry
  invisible spaces (e.g. `OrtherDataBase/ MongoDB/`), so it silently
  matches nothing - verify the stored prefix character-by-character
  against the real object key.
- **Longest-prefix wins**: when several rule prefixes contain each
  other, OSS executes ONLY the rule with the longest matching prefix;
  rules never stack and never fall back to a shorter prefix
  (measured example: rule A `trace/` -> IA, rule B `trace/archive/` ->
  Archive: key `trace/archive/file.txt` runs ONLY rule B).
- **Tag matching**: a rule with tags only touches objects carrying
  ALL configured tags; extra object tags are fine (`a:1,b:2` rule
  matches object `a:1,b:2,c:3`). Tags never apply to multipart
  fragments.
- **File-size filters**: rules may carry min/max file-size filters -
  small or large objects outside the range are skipped.
- **NOT element**: NOT scopes are per-rule; do NOT emulate multi-NOT
  by stacking rules - sibling rules' NOT elements do not affect each
  other (measured footgun: two NOT rules on `dir/p1/` and `dir/p2/`
  together delete everything under `dir/`). Multiple NOT elements in
  ONE rule exist but are invite-only (contact support to enable);
  once used, manage the rules via the console only. Official limits:
  max 1000 NOT elements per bucket, 100 per rule, and 2000 Prefix
  elements across all rules.
  **NOT mutual-exclusion constraints** (source: help.aliyun.com
  `/zh/oss/user-guide/lifecycle-rules-based-on-the-last-modified-time`):
  when NOT is enabled, fragment expiration policies
  (`AbortMultipartUpload`) cannot be configured in the same rule;
  when both min and max file-size filters are specified simultaneously,
  fragment execution policies and clear-delete-marker policies are
  also unsupported.
- **Diagnostic signal**: GET/HEAD on an object matched by an
  expiration policy returns the `x-oss-expiration` response header
  (`expiry-date` + `rule-id`) - use it to confirm WHICH rule will
  expire a given object.

## 3. Conflict & coverage semantics (rule-vs-rule)

- **Same scope, delete + transition**: the deletion action wins; the
  conflicting transition rule does not take effect.
- **Overlap rejection**: two rules whose prefixes overlap and that
  both carry the SAME action type are rejected at configuration time
  (error `Overlap for same action type Expiration`) unless the
  overlap switch is explicitly enabled; fragment-expiration rules may
  never overlap.
- **One-way transition ladder**: Standard -> IA -> Archive ->
  ColdArchive -> DeepColdArchive only. A rule converting Archive -> IA
  never executes (impossible conversion); there is no automatic
  upward path - moving back to Standard is a manual user operation.
- **Max 1000 rules** per bucket (one rule may combine last-modified
  and last-access strategies); `PutBucketLifecycle` has overwrite
  semantics (append = fetch existing rules + merge + put all).
- **Transition order constraint**: when one rule carries several
  transitions, Days MUST strictly increase along the ladder
  (IA < Archive < ColdArchive < DeepColdArchive); otherwise
  `PutBucketLifecycle` fails with `InvalidArgument: Days in the
  Transition action for StorageClass Archive must be more than the
  Transition action for StorageClass IA`.
- **ZRS note**: ZRS (zone-redundant) Standard/IA/Archive objects
  convert to LRS ColdArchive/DeepColdArchive (cold classes have no
  ZRS redundancy).
- **Conversion limits**: Appendable objects cannot be converted to
  ColdArchive/DeepColdArchive by lifecycle (seal them first);
  symlinks cannot be converted to IA/Archive/ColdArchive/
  DeepColdArchive.
- **Delete vs. restore interplay**: deleting an archived/cold object
  before its minimum storage duration elapses still bills the
  "insufficient duration" capacity fee (IA 30d / Archive 60d /
  ColdArchive 180d / DeepColdArchive 180d). Counting basis differs:
  the IA 30-day and Archive 60-day minimums count from the object's
  Last Modified time, while the ColdArchive/DeepColdArchive 180-day
  minimums count from the moment the object was CONVERTED to that
  class (source: help.aliyun.com lifecycle rule fees).

## 4. Versioning behavior

- **Expiration on the current version** (versioned bucket): OSS adds a
  delete marker; the data becomes a historical version and remains
  recoverable - it is NOT erased.
- **NoncurrentVersionExpiration**: permanently deletes noncurrent
  versions N days after they become noncurrent (irreversible). The
  noncurrent-since time can be inferred from the next version's
  last-modified time.
- **Replication caveat**: if the versioned bucket is a cross-region
  replication destination, synced delete markers demote same-name
  objects to historical versions - noncurrent cleanup rules can then
  remove data unexpectedly.
- **No historical versions on transition**: a lifecycle storage-class
  conversion does not create historical versions even when versioning
  is enabled.

## 5. Not-working attribution tree

```
Is there ANY rule on the bucket?            (GetBucketLifecycle /
  `- NoSuchLifecycle -> no_rules_configured    script finding)
        -> output a configuration TEMPLATE as advice; state the 24h
          loading window + daily 08:00 run; NEVER write the rule.
Was the rule created < 24h ago? -> loading_window (wait)
Is the rule status Enabled?       -> disabled_rules finding
Does the object key match the rule prefix exactly?
  `- no -> prefix_not_matched (literal matching, full path)
Do multiple rules match the key?  -> longest_prefix_only (single rule)
Do same-scope delete+transition rules collide?
  `- yes -> delete_beats_transition
Is the object younger than the Days spacing? -> days_policy_spacing
Versioned bucket?                 -> versioning_semantics note
```

## 6. Lifecycle request fees (why a rule costs money even when it
saves storage)

Source: help.aliyun.com "Fees related to lifecycle rules":
- **CommitTransition** (storage-class conversion): billed as Put-type
  requests, priced by the object's SOURCE class. Conversions FROM
  IA/Archive/ColdArchive cost more per request than conversions from
  Standard.
- **ExpireObject** (deletion): billed as Put-type requests priced by
  the class at deletion time; deleting a delete marker bills as
  Standard. Deleting DeepColdArchive objects by lifecycle is free of
  Put request fees; in mainland-CN regions deleting IA/Archive/
  ColdArchive by lifecycle costs more than Standard; in HK/overseas
  regions lifecycle deletion bills no Put request fees.
- **AbortMultipartUpload** (fragment expiry): billed as Put-type
  requests priced by the part's class.
Ticket pattern: a rule sweeping tens of millions of objects in one
run produces a request-fee burst that can surprise users (see
restore-guide.md sec.8).

## 7. Lifecycle DryRun (simulation before rule changes)

OSS offers a DryRun simulation for lifecycle (source: help.aliyun.com
"Lifecycle DryRun", `/zh/oss/user-guide/lifecycle-dryrun`):
before creating/modifying/disabling/deleting rules, DryRun replays
ALL rules of the bucket against an inventory snapshot and predicts
future capacity trends and deletion volumes - simulate only, never
executes. Constraints to relay:
- **Hard prerequisite**: the bucket's default storage class must be
  **Standard or Infrequent Access** - DryRun cannot run and produces
  no report on buckets whose default storage class is Archive,
  ColdArchive, or DeepColdArchive.
- Whitelist-gated (support ticket) and limited to a fixed region list.
- Whole-bucket granularity only (no per-prefix/per-rule simulation).
- The changed rule stays pending until manually applied.
- The report is a snapshot prediction, not an audit or exact cost
  estimate.
- **Not instant**: DryRun first generates an inventory scan (duration
  proportional to data volume), then the report takes an additional
  tens of minutes to several hours on top of the inventory generation
  time.
- Associated costs: inventory request fees + report/inventory storage
  and read fees.
Advise it whenever a rule change could delete or sink large amounts
of data (this skill itself never applies rules).

## 8. Configuration template (advice only - ABSOLUTE PROHIBITION:
this skill NEVER calls PutBucketLifecycle)

Console path: Bucket -> Data Management -> Lifecycle -> Create Rule.
Equivalent PutBucketLifecycle XML shape for the user to apply:

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>tier-logs-to-ia</ID>
    <Prefix>logs/</Prefix>
    <Status>Enabled</Status>
    <Transition><Days>30</Days><StorageClass>IA</StorageClass></Transition>
    <Transition><Days>180</Days><StorageClass>Archive</StorageClass></Transition>
    <Expiration><Days>730</Days></Expiration>
  </Rule>
</LifecycleConfiguration>
```

Remind the user: overwrite semantics (include existing rules), the
24-hour loading window, and the daily 08:00 Beijing-time run.
