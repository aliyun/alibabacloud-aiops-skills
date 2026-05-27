# Step 0: Resolve `$SKILL_DIR` — Cross-Platform Path

> **Why**: This skill ships a Python toolkit at `<skill-root>/scripts/deploy_toolkit.py`. Different agent platforms install skills to different locations:
> - **Qoder**: `~/.qoder/skills/alibabacloud-ecs-code-deploy/` (or alias `~/.qoder/skills/deploy-to-ecs/`)
> - **Claude Code**: `~/.claude/skills/<name>/` (user-scope) or `<project>/.claude/skills/<name>/` (project-scope)
> - **Qwen**: `~/.qwen/skills/<name>/` or `<project>/.qwen/skills/<name>/`
> - **Other / custom**: anywhere reachable via `$SKILLS_HOME` or explicit env var
>
> The Agent MUST resolve the absolute skill root **once** at session start and reuse it everywhere `$SKILL_DIR` appears in `SKILL.md`. **Hardcoding `~/.qoder/...` or any platform-specific path is FORBIDDEN.**

## Resolution algorithm — use the FIRST path that exists

The Agent MUST check these candidates in order and pick the first one whose `scripts/deploy_toolkit.py` exists:

1. **The directory the Agent loaded THIS `SKILL.md` from** (PRIMARY — Agent runtime metadata; most accurate, platform-independent)
2. `$ALIBABACLOUD_ECS_CODE_DEPLOY_SKILL_DIR` (explicit override env var)
3. `$SKILLS_HOME/alibabacloud-ecs-code-deploy` (generic skills home env var)
4. `~/.qoder/skills/alibabacloud-ecs-code-deploy` (Qoder default)
5. `~/.qoder/skills/deploy-to-ecs` (Qoder alias)
6. `~/.claude/skills/alibabacloud-ecs-code-deploy` (Claude Code user-scope)
7. `./.claude/skills/alibabacloud-ecs-code-deploy` (Claude Code project-scope, relative to CWD)
8. `~/.qwen/skills/alibabacloud-ecs-code-deploy` (Qwen user-scope)
9. `./.qwen/skills/alibabacloud-ecs-code-deploy` (Qwen project-scope, relative to CWD)
10. `~/.config/skills/alibabacloud-ecs-code-deploy` (XDG-style fallback)

## Export and verify (run ONCE at session start, before Step 1)

```bash
# Replace <ABSOLUTE_PATH> with the path resolved above (NEVER guess — verify it exists first)
export SKILL_DIR="<ABSOLUTE_PATH>"

# Sanity check — script file must exist
test -f "$SKILL_DIR/scripts/deploy_toolkit.py" || {
  echo "❌ Toolkit script not found at: $SKILL_DIR/scripts/deploy_toolkit.py"
  echo "   Agent: ask the user where the skill is installed, OR fall back to manual CLI commands."
  exit 1
}
echo "✅ SKILL_DIR=$SKILL_DIR"
```

## Usage convention

All `SKILL.md` commands write `python3 "$SKILL_DIR/scripts/deploy_toolkit.py" <subcmd>`. The Agent must turn that template into a real, working command **using ONE of the two patterns below**. A third pattern that LOOKS correct but silently breaks is documented as a forbidden anti-pattern.

### ✅ Pattern A — persistent shell (recommended when the platform reuses one shell)

```bash
# Run ONCE at session start (e.g. after Step 0 verification)
export SKILL_DIR="/absolute/path/to/skill"

# Then every later command can reference $SKILL_DIR normally
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check
```

### ✅ Pattern B — fresh shell per tool call (recommended when each command is a NEW shell)

Inline the absolute path directly. **Do NOT use `$SKILL_DIR` in this case.**

```bash
python3 "/home/user/.qwen/skills/alibabacloud-ecs-code-deploy/scripts/deploy_toolkit.py" check
```

If you really want a variable for readability, set + use it inside ONE shell invocation:

```bash
bash -c 'SKILL_DIR="/home/user/.qwen/skills/alibabacloud-ecs-code-deploy"; python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check'
```

### ⛔ Anti-pattern — DO NOT USE (silently fails)

```bash
# THIS DOES NOT WORK. $SKILL_DIR is expanded by the OUTER shell BEFORE the
# command-prefix assignment takes effect, so it expands to the empty string and
# python3 ends up trying to open "/scripts/deploy_toolkit.py" → ENOENT.
SKILL_DIR="/home/user/.qwen/skills/alibabacloud-ecs-code-deploy" \
  python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check
```

Why it fails: in POSIX shells, command-prefix variable assignments (`VAR=value command ...`) only populate the child process's environment. Quoted `"$VAR"` on the same line is expanded by the parent shell **before** the assignment is applied — at which point `$VAR` is still unset/empty. The error you'll see looks like:

```
python3: can't open file '/scripts/deploy_toolkit.py': [Errno 2] No such file or directory
```

If you ever see that exact error, the cause is this anti-pattern — switch to Pattern A or B.

## Fallback

If none of the candidates above contain `scripts/deploy_toolkit.py`, the Agent MUST stop and either ask the user where the skill is installed, or follow the manual CLI flow documented in `SKILL.md` Task 1/Task 2. Do NOT silently re-implement the toolkit logic with raw commands.
