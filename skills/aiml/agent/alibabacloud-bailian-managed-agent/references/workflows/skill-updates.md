# Check this skill's version and offer an optional update

This skill uses calendar releases: **`vYYYYMMDD`**, currently **`v20261015`**. Keep the version in `SKILL.md`'s frontmatter `description` and `references/manifest.json` identical. Use the release date, not the CLI/SDK version. A new release that should trigger an update must have a strictly later date; multiple edits published under the same date do not trigger replacement.

## Invocation

Resolve `SKILL_ROOT` from the loaded skill's location, not the user's project directory. Python 3 and its standard library are sufficient:

```bash
# Default: check only; do not download or replace files.
python3 "$SKILL_ROOT/scripts/check_for_updates.py"
```

On `update_available`, show both versions and ask once, for example: **“The installed skill version is `<local_version>`, and a newer version `<remote_version>` is available. Would you like to update? You can continue the current task without updating, but the skill's knowledge may be outdated.”** Invoking the skill or discovering a version difference does not authorize an update. Reuse explicit approval already given for this update; otherwise wait for approval before installing. If the user declines or has not answered, continue the original task with the installed copy. Do not repeatedly prompt for the same release in this conversation or block the task on an update.

Only after explicit user approval, run the following command. Set `BAILIAN_MANAGED_AGENT_SKILL_UA` to the initial check's JSON `user_agent` value so the approved update preserves this invocation's session ID:

```bash
python3 "$SKILL_ROOT/scripts/check_for_updates.py" --apply \
  --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA"
```

Each helper call makes one metadata GET; the approved apply call rechecks before installing. Download only when the remote version is strictly newer and the user has approved updating. No API key, login, or cloud resource operation is needed. The helper returns JSON; use its `user_agent` value for subsequent cloud requests in this invocation. After an approved update, use the apply result's UA, which retains the supplied session ID and changes the version to the installed release. If no update occurs, keep the local version in the UA.

## Registry contract

- Metadata: `GET https://skills.aliyun.com/api/public/skills/alibabacloud-bailian-managed-agent`
- ZIP: `GET https://skills.aliyun.com/api/public/skills/alibabacloud-bailian-managed-agent/download`
- Verified 2026-10-15: metadata has `code: 200`, `data.skillName`, `data.content` (the complete SKILL.md), and `data.updatedAt`. The ZIP currently has `SKILL.md` at its root. The helper also accepts one enclosing directory.
- Extract the version only from the frontmatter **description** in `data.content`; validate its calendar date before comparing. Do not treat `updatedAt`, dates in body examples, or the registry's marketing description as a release version.
- The currently published legacy package has no description date version and a manifest version of `0.0.1`. Return `version_unknown` and retain the local installation. Publishing this release must update both the metadata's SKILL.md content and the downloadable package.

`data.content` is a string, not a nested JSON object. After publishing this release, a versioned response should have this shape (excerpt):

```json
{
  "code": 200,
  "data": {
    "skillName": "alibabacloud-bailian-managed-agent",
    "content": "---\nname: alibabacloud-bailian-managed-agent\ndescription: |-\n  Version v20261015 (date-based release, YYYYMMDD).\n  Explain, evaluate, demonstrate, provision, and integrate Alibaba Cloud Bailian\n  Managed Agent (CMA / ManagedAgents).\n---\n"
  }
}
```

Decode the API response as JSON first; its `\n` escapes become real line breaks in `data.content`. Then read that string's YAML frontmatter description to extract `v20261015`. A description with no version, such as the legacy text starting directly with “Explain, evaluate…”, has no comparable release version.

## Results and recovery

| `status` | Action |
| --- | --- |
| `up_to_date` | Continue with the installed copy. |
| `local_newer` | Report that the local version is newer than the registry; keep it without downloading or downgrading. |
| `update_available` | Report both versions and the risk of outdated knowledge; ask whether to update. Install only with explicit approval. If declined or unanswered, continue with the installed copy. |
| `updated` | Report old/new versions, installation and backup paths. Reread updated instructions and relevant files without repeating this invocation's check. |
| `version_unknown` | Explain that the registry has no comparable date version; continue with the local copy. |
| `source_checkout` | A newer release exists, but the skill is in a Git source checkout. Report it; do not replace source files with a release ZIP. |
| `error` | Report the check/update failure and continue with the existing copy. Do not claim it is the latest. If automatic restoration failed, recover the installation from the reported backup path before using the skill again. |

The helper validates the skill name, ZIP paths, file types, size limits, description version, and manifest version before replacing files. It never runs downloaded scripts. It keeps the previous installation in a hidden sibling directory (`.skill-update-backups`), stages replacement on the same filesystem, and restores the backup if the final rename fails. It does not alter other skills, host settings, credentials, or project files. Filesystem permissions still apply; use the host's normal permission mechanism if required rather than writing to a different installation silently.

After a successful install/update, tell the user: **“The skill has been updated to `<version>`. We recommend starting a new conversation to refresh the loaded skill list and description. The updated files have been reread in this conversation, but the host's cache may not have refreshed.”** For hosts with a verified reload mechanism, use that mechanism and explain whether a new conversation is still needed. Do not claim the host reloaded merely because the files changed.
