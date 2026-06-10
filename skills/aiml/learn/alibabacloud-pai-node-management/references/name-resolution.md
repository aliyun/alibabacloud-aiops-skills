# Name-to-ID Resolution (prerequisite when user supplies a name)

If the user provides a **Resource Group name** or **Quota name** instead of an ID, the agent MUST resolve it to a `ResourceGroupId` before any node call.

## Case A — user provides a Resource Group name

```bash
aliyun paistudio list-resource-groups \
  --region "${REGION_ID}" \
  --name "${RG_NAME}" \
  --page-number 1 --page-size 50
```

- Exactly **one** match → use its `ResourceGroupId`.
- **Multiple** matches → present a candidate table (`ResourceGroupId | Name | ResourceType | Status`) and ask the user to pick.
- **Zero** matches → paginate end-to-end (`--page-number 1..N`) for partial / fuzzy matches; surface candidates or report *"no match"*.

## Case B — user provides a Quota name

```bash
aliyun paistudio list-quotas \
  --region "${REGION_ID}" \
  --quota-name "${QUOTA_NAME}" \
  --layout-mode Tree \
  --page-number 1 --page-size 50
```

- Read `ResourceGroupIds` (array) from the matching Quota.
- **One** RG → use it directly.
- **Multiple** RGs → either loop `list-nodes` per RG, or ask the user to narrow down.
- **Zero** matches → paginate; surface candidates or report *"no match"*.

After resolution, proceed with the resolved `RESOURCE_GROUP_ID` (or pass `--quota-id` directly if the user's intent is Quota-scoped).
