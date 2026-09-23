# Automatic Skills updates

In the current user session, run `dtscli version --json` only the first time this Skill is used. Confirm that capabilities contains `skills.ensure`, then run:

```bash
dtscli skills ensure --agent <agent>
```

Later steps and sub-agents in the same session run business commands directly and do not run `version --json` or `skills ensure` again.

`--agent` is required and must match `[a-z][a-z0-9_-]{0,31}`. Supply the host where this Skill is installed. The default directory is `~/.<agent>/skills`; `opencode` uses `~/.config/opencode/skills`, and `qwencode` uses `~/.qwen/skills`. For a different installation, add `--directory "<absolute-skills-directory>"`, pointing to the parent containing the Skill packages, to avoid checking another installation. `--agent` on `skills install` / `skills ensure` selects the install directory; `--agent` on business commands is the DTS-AI call source.

The first CLI release is `2.0.0` and includes `skills.ensure`; no pre-release CLI compatibility or migration workflow is needed. If the CLI is missing, follow the existing installation authorization workflow. If an installed CLI lacks this capability, stop and check PATH and the installed artifact as an installation integrity issue; do not run a legacy migration or loop over upgrade.

## Cache and scope

- `skills ensure` and `skills install` both update the CLI first, then use the **current CLI** to install or update Skills. The two rolling 24-hour caches are separate: CLI under `~/.aliyun-dts/updates/cli/`, Skills under `~/.aliyun-dts/updates/skills/`, both respecting `DTS_STATE_ROOT`. Do not delete the cache or repeatedly retry to bypass this limit.
- Installations with valid package identity metadata participate by default. The CLI checks only DTS Skills already installed in the selected directory and automatically reads each package's name, version, and minimum CLI; it does not add other skills. A package leaf that is a symlink is resolved and checked against the real directory; the link target is never replaced. Catalog checks use this CLI's Skills source. Directories without valid package identity metadata stay `unmanaged`. Reinstall an old package once from the joint release to identify it.
- The CLI automatically fetches the latest release manifest from its own distribution source. A newer CLI is installed first, then the new `dtscli` continues. Each Skill's release manifest is fetched from this CLI's Skills source, one manifest per package. Caches are separate for each Skill source; Agents share the cache for the same Skill. Test and production caches are isolated by source.
- Updates install a newer catalog version only. Same-version content changes are not replaced. If the current CLI is still below a package's minimum, keep the old package (`dependency_failed`). Never automatically downgrade.
- ZIP size, SHA-256, paths and file inventory are validated, then local files are checked again for edits. Preserve local edits, extra/missing files and links. Failed replacements restore the old package; business commands are never automatically replayed.

## Results and next steps

stdout contains JSON; progress goes to stderr. Check `ready` and `reload_required`, not just the exit code.

| Result | Action |
| --- | --- |
| `ready=true` | The installed version may continue its existing workflow; other authorization rules still apply. |
| `action=busy` | Another process is updating. Continue the business command when `ready=true` because installed packages already meet the current CLI; you may wait a few seconds and retry ensure once. |
| `reload_required=true` | The CLI or Skills changed. Stop the current workflow and reload Skill files. If the host cannot refresh, ask the user to open a new session and verify that PATH uses the new CLI. Already loaded instructions do not refresh automatically. |
| `ready=false` without reload | Stop and resolve dependencies or local recovery before continuing. |
| `current`, `newer_local`, `not_listed` | Content unchanged, local version newer, or absent from the catalog; no deletion or downgrade. |
| `unmanaged`, `local_changes` | Preserve old installations, symlink targets that cannot be replaced, or local edits; continue only when `ready=true`. Obtain the user's choice before reinstalling over edits to enable updates. |
| `check_failed`, `update_failed`, `dependency_failed` | Preserve the old package; use `ready` to decide whether the existing workflow can continue. Stop if its dependency is unmet. Do not repeatedly download. |
| `recovery_required` | Stop and inspect the adjacent `<skill>.dts-backup`; do not delete it automatically. |

Top-level `action` is `completed`, `disabled`, `busy` or `unmanaged`. `cli` is this invocation's CLI check, where `state=skipped` means no manifest was fetched. Package states appear in `skills[].state`. Configuration errors or corrupted state use the common `error_class` output and a nonzero exit code; stop and address the error.

To disable automatic updates, users set `export DTS_SKILLS_AUTO_UPDATE=0` on macOS/Linux or `$env:DTS_SKILLS_AUTO_UPDATE='0'` in PowerShell. Set it to `1` or remove it to restore the default. Disabling updates does not waive known minimum CLI requirements. Do not override the user's opt-out.

Each Skill has its own version and minimum CLI dependency. Each package has its own manifest containing only its entry; fetch the selected package from `releases/<skill-name>/<version>.zip`. Do not infer that other Skills must upgrade to the same version.
