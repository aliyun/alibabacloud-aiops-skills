# End-to-end playbooks

Use these playbooks to avoid partial completion. Each playbook requires
"write + read-back verification" before reporting success.

## Shared verification rules

For every mutating step:

1. Check write JSON result: `success`, `operation`, `data`, `error`.
2. Run corresponding read command in the same region/resource scope.
3. Verify concrete expected fields, not only "command succeeded".
4. If read-back is delayed, retry read up to 3 checks before deciding failure.

## 0) Core lifecycle (create -> tag/untag -> query -> delete)

1. Run `create --confirm` and capture returned `InstanceId`.
2. Run `describe --region_id <region>` until target instance is visible/operable.
3. Run `tag_resources --confirm` for the same `InstanceId`.
4. Run `list_tags` and verify expected tag key/value pairs exist.
5. Run `untag_resources --confirm` for the same `InstanceId`.
6. Run `list_tags` and verify removed keys are absent.
7. Run `describe --region_id <region>` and verify target instance still exists before delete.
8. Run `delete --force_confirmation` for the same `InstanceId`.
9. Run `describe --region_id <region>` and verify target instance is absent.

Hard rules:

- Same-instance continuity: all lifecycle steps must use the same `InstanceId`.
- No substitution: do not switch to another running instance to "complete" the
  chain unless user explicitly approves.
- If target instance is still provisioning, keep read-checking readiness first;
  if timeout occurs, report `incomplete` with blocker.

## 1) Create instance (PayAsYouGo)

1. Run `create --instance_type PayAsYouGo --confirm`.
2. Run `describe --region_id <region>`.
3. Verify the target instance appears by `InstanceId` or unique `InstanceName`.
4. Verify instance resource spec matches requested CPU/memory.

Done when:

- `create` write result is success
- `describe` confirms instance presence and expected spec

## 2) Create namespace

1. Run `describe --region_id <region>` and verify target instance exists.
2. Run `describe_namespaces` and check whether target namespace already exists.
3. If namespace does not exist: run `create_namespace --confirm`.
4. If namespace already exists: treat as idempotent success only when existing
   spec matches expected; otherwise report mismatch and remediation.
5. Run `describe_namespaces` for the same instance.
6. Verify namespace exists; if CPU/memory was requested, verify spec matches.

Done when:

- namespace exists in `describe_namespaces`
- expected namespace spec is verified (or explicitly confirmed unchanged)

## 3) Upgrade instance spec

1. Run `describe --region_id <region>` and record current spec.
2. Run `modify_spec --confirm_price`.
3. Run `describe --region_id <region>` again.
4. Verify target instance CPU and memory reflect new CU count.

Done when:

- `modify_spec` returns `success: true`
- follow-up `describe` shows updated spec

## 4) Tag resources

1. Use canonical `--resource_type vvpinstance` unless user explicitly requests
   another valid type.
2. Run `tag_resources --confirm`.
3. Run `list_tags` for the same resource IDs.
4. Verify each expected `key:value` exists in returned tags.
5. For batch resource IDs, verify each target resource has expected tags.

Done when:

- `tag_resources` write result is success
- `list_tags` confirms all expected tags per target resource

## 5) Delete instance cleanup

1. Run `describe_namespaces` for target instance.
2. Build removable namespace list:
   - always skip `default`
   - skip system/internal namespaces that are non-removable
3. Delete removable namespaces with `delete_namespace --confirm`.
4. Run `describe_namespaces` again and confirm removable namespaces are absent.
5. Run `delete --force_confirmation`.
6. Run `describe --region_id <region>` and confirm target instance is absent.

Done when:

- namespace cleanup and instance deletion writes are successful (or already-absent
  idempotent equivalent)
- follow-up reads confirm no removable namespace leftovers and no instance

## 6) Modify namespace spec (guardrail)

1. Run `describe_namespaces` and verify target namespace exists.
2. Run `modify_namespace_spec --confirm --ha <true|false>`.
3. Run `describe_namespaces` again and verify spec changed as expected.

Hard rules:

- Do not auto-create namespace when modify fails.
- If namespace does not exist, stop and ask user whether they want an explicit
  `create_namespace` operation.

## 7) Batch operation checklist

When request includes multiple targets (IDs/names/tags):

1. Parse all items in input order.
2. For each item: execute write -> run read-back verification -> record status.
3. Continue remaining items after single-item failure unless all-or-nothing is required.
4. Return per-item final table (`item`, `write`, `verify`, `status`, `reason`).
