# PDS Drive Concepts and API Reference

**Scenario**: Query a user's drives (personal / team / enterprise space).
**Purpose**: Obtain the `drive_id` of the target space.

---

## Drive Concept

A PDS drive is a cloud storage space owned by a user or a group:
- Owned by a **user** → personal space.
- Owned by an **enterprise group** → enterprise space.
- Owned by a **team group** → team space.

A user has three space types in a domain: enterprise, team, personal. **"My PDS drive" without a specified type means all of them.**

Key Drive fields: `drive_id` (unique ID, used by most other APIs), `drive_name`, `total_size`, `used_size` (bytes), `owner_type` (`user`/`group`), `owner`.

---

## Recommended: list all drives in one call

`aliyun pds list-all-drives` returns personal, team, and enterprise drives together (paginated and de-duplicated internally), each summarized to the fields above.

```bash
aliyun pds list-all-drives
```

**Output**:
```json
{
  "drives": [
    {"drive_id": "108", "drive_name": "SuperAdmin", "space_type": "personal", "owner_type": "user",  "total_size": 107374182400, "used_size": 950709133},
    {"drive_id": "103", "drive_name": "Test Space", "space_type": "enterprise", "owner_type": "group", "total_size": 107374182400, "used_size": 240062520},
    {"drive_id": "100", "drive_name": "Team Space 1", "space_type": "team", "owner_type": "group", "total_size": 107374182400, "used_size": 138194}
  ],
  "count": 3
}
```

Use `space_type` to pick the right drive.

> **If `list-all-drives` returns a 403 (no-permission), fall back — do NOT terminate.** That 403 only means the current user lacks the domain-level "list all drives" permission; it does **not** mean the user has no accessible spaces. Enumerating the user's **own** drives is a separate, normally-allowed capability: immediately retry the listing with the per-type commands below (`list-my-drives` for personal + `list-my-group-drive` for team/enterprise), then answer from their combined result. Only report a permission problem / suggest contacting the administrator if those per-type calls **also** fail with 403. This is a documented recovery, not a "blind retry" — do not re-run `list-all-drives` itself.

### Resolve the drive once, then reuse it (do NOT re-query)

`drive_id` is **stable** for a given `(domain_id, user_id, space_type)` — it does not change during a task. Therefore:

- **Call `list-all-drives` at most once per task.** Its single response already contains the personal, team, and enterprise drives together.
- **Record the `drive_id`(s) you need from that one response and reuse them for every subsequent command** (`upload-file`, `resolve-path`, `search-file`, `get-download-url`, `image-process`, `archive-download`, …). Do not call `list-all-drives` / `list-my-drives` / `list-my-group-drive` again just to re-fetch a `drive_id` you already have.
- If the task touches multiple space types, pick all the needed `drive_id`s from that same single response in one pass.
- Only re-query if a later command fails with a drive-not-found / permission error, which may indicate the drive set changed.

This avoids redundant round-trips: each extra drive listing is 2+ backend API calls plus an extra agent turn, with no new information.

---

## Per-type queries (when you need raw drive objects)

**Enterprise + team space** — `items` holds team spaces, `root_group_drive` holds the (at most one) enterprise space:
```bash
aliyun pds list-my-group-drive --limit 100 --marker ""
```

**Personal space** — `items` holds personal drives:
```bash
aliyun pds list-my-drives --limit 100 --marker ""
```

Both paginate via `next_marker`: if it is non-empty, pass it as `--marker` on the next call until it is empty. Each returned item is a Drive object with the fields listed above.
