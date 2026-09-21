# references/ Index (Cross-Workflow Shared Reference)

> This directory is the on-demand deep-read supplement of [SKILL.md](../SKILL.md); it only holds reference docs **shared across workflows**. **Single-workflow self-contained assets** (`<biz>.md` / `schema.yaml` / `form.html` / `lib/*.sh`) have been moved to the [workflows/<biz>/](../workflows/README.md) subdirectories. The Agent normally only reads the SKILL.md index; when performing mutating operations it follows SKILL.md links over here. This README only does **navigation** and does not duplicate content.

## Dual-View Guide

| View | Recommended entry |
|---|---|
| **Agent runtime** (read on demand) | Before entering a business flow, read SKILL.md to trigger the corresponding section → jump to the matching [workflows/<biz>/<biz>.md](../workflows/README.md) to finish parameter collection and mutating; workflows/<biz>/schema.yaml is force-read by `lj_init.sh` and `extend_form` during R1/R2 |
| **Developer onboarding** (read in order) | `detailed-rules.md` → [`workflows/extend-cluster/extend-cluster.md`](../workflows/extend-cluster/extend-cluster.md) / [`workflows/shrink-cluster/shrink-cluster.md`](../workflows/shrink-cluster/shrink-cluster.md) / [`workflows/create-node-group/create-node-group.md`](../workflows/create-node-group/create-node-group.md) (see the full R1/R2 chain) → `scripts.md` (see how lib/ scripts are invoked in the documentation context) → `edge-cases.md` (see common error fallbacks) → [`workflows/<biz>/schema.yaml`](../workflows/README.md) (see the exact schema constraining the agent) |

## Files in This Directory (10 Cross-Workflow Shared References)

### API Reference

| File | One-line responsibility | Agent runtime | Developer must-read |
|---|---|:---:|:---:|
| [api-parameters.md](./api-parameters.md) | Repo-unique parameter traps (ListNodeGroups GroupId field, field comparison table) | ✅ (on demand) | ✅ |
| [error-codes.md](./error-codes.md) | Complete eflo-controller OpenAPI error code set (verified 3 times against source) | ✅ (error recovery) | ✅ |
| [command-quick-reference.md](./command-quick-reference.md) | One-line quick reference for high-frequency CLI commands | — | ✅ |
| [endpoint-routing.md](./endpoint-routing.md) | Sole detailed implementation of the Region Required hard rule (B-6 explained) | ✅ | ✅ |
| [supported-regions.md](./supported-regions.md) | Static fallback region table (at runtime prefer the `describe-regions` API) | — | — |
| [ram-policies.md](./ram-policies.md) | RAM policies and permission sets (read before production management-plane installation) | — | ✅ |
| [cli-installation-guide.md](./cli-installation-guide.md) | aliyun CLI 3.3.3+ installation and configuration | — | ✅ |

### Developer Reference

| File | One-line responsibility | Agent runtime | Developer must-read |
|---|---|:---:|:---:|
| [detailed-rules.md](./detailed-rules.md) | On-demand deep-read supplement of SKILL.md hard rules (L0-L10) | ✅ (on violation) | ✅✅✅ |
| [edge-cases.md](./edge-cases.md) | Edge scenarios and error handling (includes the `safe_aliyun` implementation skeleton Appendix B.4) | ✅ (error recovery) | ✅✅ |
| [scripts.md](./scripts.md) | Reusable bash script snippets in the docs (after `source ./lib/lj_init.sh`, call `query` etc.) | — | ✅ |

## Business Flow Deep Read → workflows/

13 vertical slices have been moved out of this directory; each workflow is self-contained with `<biz>.md` / `schema.yaml` / `form.html` / `lib/*.sh`:

| Category | Workflow subdirectory |
|---|---|
| Business flows (mutating) | [extend-cluster](../workflows/extend-cluster/extend-cluster.md) · [shrink-cluster](../workflows/shrink-cluster/shrink-cluster.md) · [create-node-group](../workflows/create-node-group/create-node-group.md) · [update-node-group](../workflows/update-node-group/update-node-group.md) · [change-node-group](../workflows/change-node-group/README.md) · [delete-hyper-node](../workflows/delete-hyper-node/delete-hyper-node.md) · [delete-node](../workflows/delete-node/README.md) · [create-instance](../workflows/create-instance/README.md) · [node-operations](../workflows/node-operations/node-operations.md) |
| Queries (read-only) | [cluster-query](../workflows/cluster-query/cluster-query.md) · [hyper-node-query](../workflows/hyper-node-query/hyper-node-query.md) · [node-group-query](../workflows/node-group-query/node-group-query.md) · [machine-image-query](../workflows/machine-image-query/machine-image-query.md) |

Top-level index: [workflows/README.md](../workflows/README.md).

## Naming and Renaming Notes

The lib/ function names in this directory's examples follow the post-governance naming convention (`extend_form` / `extend_submit` / `query` / `shrink_form` / `create_node_group_form` etc.); see [`../lib/README.md`](../lib/README.md).

## Do-Not-Change List (Protected Boundaries)

- Inter-document links (paths and file names) — changing them = 30+ link cascade
- workflows/<biz>/schema.yaml detection_anchor and field names — agent parsing depends on them
- envelope prefixes `[LJ_EXEC_NOW_EXTEND]` / `[LJ_EXEC_NOW_CREATE_NG]` and all `===*===` sentinels — widget and agent protocol layer
