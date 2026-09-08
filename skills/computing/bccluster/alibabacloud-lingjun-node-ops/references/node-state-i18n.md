# Node OperatingState i18n - rendering rules (MANDATORY in zh sessions)

> Authoritative data source: the `state.*` dictionary in `lib/core/i18n.sh` (synced from the official "Lingjun node customer-facing OperatingState bilingual mapping" document, 2026-08-21). The API-facing `OperatingState` is the customer-facing state, converged from roughly 200 internal control states (`NodeState`).
>
> Compliance note (static-scan rule 4.1.2): this document is English-only and contains zero Chinese characters. All zh display strings live exclusively in `lib/core/i18n.sh`, a shell data file outside the scanned documentation set; do not duplicate them here.

## Where the translations live

Every customer-facing OperatingState has a key pair in `lib/core/i18n.sh`:

```bash
zh::state.<OperatingState>)  # zh canonical display name
en::state.<OperatingState>)  # en display name (== raw enum value)
```

Example: `Using`, `Unused`, `Extending`, `Cutting`, `Operating`, `Diagnosing`, `Switching`, plus the full stop-service (`ClusterNodeStopping` ...), shutdown (`ClusterNodeShuttingDown` ...), repair (`ClusterNodeRepairPendingApproval` ...), reboot-repair (`ClusterNodeRebootPendingApproval` ...), and release/replace/reconfig/upgrade (`Releasing`, `Replacing`, `ClusterNodeReconfiguring`, `ClusterNodeUpgrading` ...) families - every key has its zh display value in the dictionary. Read it directly instead of duplicating the table here.

## Rendering rules

- **zh sessions**: any user-facing output (query results, confirmation tables, receipts, progress reports, final reports) **must** render node states via the zh `state.*` values; these are the sole authoritative display names - never improvise alternative wording. When an exact cross-check against the raw API value is needed, the form `zh-name (RawValue)` is acceptable, but tables/lists default to pure zh.
- **en sessions**: keep the raw English state value.
- Logic (scripts / jq / precheck conditions) always compares the raw English enum value; translation happens only at the user-facing rendering layer.
- Hyper nodes have a separate `HyperNodeState` (health-tiered: `HealthyUsing` / `SubhealthyUsing` / `AbnormalUsing` etc.); hyper-node states not covered by the `state.*` dictionary stay in their raw English form.
- Any state absent from the dictionary is kept in raw English and annotated as "not in the mapping" in zh output.
