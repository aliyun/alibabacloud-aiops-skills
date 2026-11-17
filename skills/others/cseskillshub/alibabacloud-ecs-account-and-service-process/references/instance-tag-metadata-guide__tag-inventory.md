# Instance tags: what the API returns, naming rules, inventory method

Tags are the other half of this tier's ownership question: a resource group
decides *who may act*, tags say *what something is*. Both are readable facts on
the instance record, and both are things the customer changes elsewhere -- this
skill only reads them back.

Evidence labels: `api:` = verified against the live read API; `ticket:` = a
support conversation that was read in full; `summary:` = a ticket summary whose
conversation was NOT re-pulled. Cross-checked **2026-08**; shapes live-verified
**2026-09-18**.

## 1. How tags arrive in the response

The instance listing carries a tag array per instance; each element has a tag key
and a tag value, and an empty value is legitimate (`api:DescribeInstances`). The
entry script surfaces them as `key=value` pairs (or the bare key when the value
is empty) in the facts block.

Two things the listing also shows, which matter for an honest inventory:

- **Service-created keys.** Keys carrying the reserved `acs:` prefix are written
  by Alibaba Cloud, not by the customer -- `acs:tag:createdby`, which records
  which identity created the instance, appeared on every console-created
  instance in the live check. The inventory block counts customer keys separately
  and says so; an instance whose only tag is a service key is reported as
  "without a customer tag".
- **The group id sits next to the tags.** An instance can carry a perfect tag set
  and still be invisible in a resource-group view, or the other way round. Report
  both fields together rather than answering "is it tagged / is it in the group"
  from one of them.

The listing filter accepts a single tag key and an optional tag value
(`Tag.1.Key`, `Tag.1.Value`). The dedicated tag-listing action is not part of
this skill's verified surface, so all tag facts here come from the instance
record itself.

## 2. Naming rules as they are asked in tickets

The recurring intake question is a form field, not an API problem: "what is a tag
key, and do I have to fill it in?" The answer given in the source conversation:

- the field may be left empty -- a name alone is enough to proceed
  (`ticket:0005PR5NGW`);
- a name of **2 to 128 characters**, starting with a letter (either case) or a
  Chinese character, and **not** starting with an `http://` or `https://` prefix
  (`ticket:0005PR5NGW`, quoted from the agent's reply);
- the same conversation's unrelated warning that a key-pair private key file can
  be downloaded only once belongs to the key-pair flow, not to tags; it is
  reproduced here only because customers ask both in one breath. Login and
  key-pair questions go to `alibabacloud-ecs-keypair-login-config`.

Design guidance this skill can defend from the field semantics rather than from
opinion: one key per dimension (business line, environment, owner, cost centre)
keeps later filtering possible; encoding several dimensions into one value
(`prod-web-teamA`) makes the tag unfilterable, and the listing filter matches a
key plus a value, not a substring.

## 3. Inventory method

```bash
python3 scripts/axes/instance_tag_metadata_guide/ecs_instance_tag_metadata_check.py \
  --region cn-hangzhou --region cn-beijing --inventory --json
```

A locator-free run needs `--inventory`: without it the script stops at the
"no target named" gate, ends `STATUS: FAIL` and prints the visible records as a
pick-list instead of an inventory.

The `TAG INVENTORY` block reports:

| Field | Meaning |
|---|---|
| `instances_scanned` | instance records read for the locators in force |
| `untagged_instance_ids` | records with no customer tag at all |
| `tag_keys` | key -> how many scanned instances carry it |
| `keys_with_conflicting_values` | keys carrying more than one distinct value across the fleet |
| `service_created_tag_prefix` | the reserved prefix excluded from the counts above |

Interpretation rules:

- Zero instances scanned is not "zero tags": it means the locators matched
  nothing in the regions queried. Say which regions were read.
- `keys_with_conflicting_values` is a finding to report, not an error to fix:
  `env=prod` and `env=production` on the same key is a naming drift a human has
  to decide about.
- The inventory is per-region and per-credential. A fleet-wide statement needs
  every region listed and one account per run.
- Tagging, retagging and removing tags are console actions the customer performs;
  after they do, re-run the same command and compare the before/after output.

## 4. Tag-driven behaviour that is documented

- Applying an automatic snapshot policy by tag (the policy follows the instances
  carrying a given tag) is documented for the instance itself:
  <https://help.aliyun.com/zh/ecs/user-guide/apply-an-automatic-snapshot-policy-to-the-instance.md>
  Read it as a rule statement: this skill neither creates nor attaches a
  snapshot policy, and coverage review of snapshot policies belongs to
  `alibabacloud-ecs-snapshot-policy-check`.
- Whether a feature exists at resource-group scope at all is answered by the
  feature catalogue:
  <https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md>

## 5. Not covered here, stated honestly

- **Tag-based cost allocation / bill split by tag.** No ticket in this tier's
  evidence set raised it as the main complaint and no verified documentation URL
  was found for it, so this skill makes no promise about it and refers the
  customer to the billing channel instead.
- **Bulk tag planning across accounts.** Reads are limited to the account behind
  the current credential; a second account needs its own credential profile.
- **Enforcement of a tagging convention.** Deciding "an instance must carry
  owner + env" and blocking what does not is a governance configuration the
  customer owns; this skill can only report the current gap list.
