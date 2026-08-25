# Dgate CLI routing

Use the `dgate` binary selected by the user. Do not substitute a DMS database-management CLI or a direct database client.

Resolve the runtime once before the first command and reuse that exact executable for the rest of the turn:

1. Use `command -v dgate` when `dgate` is available on `PATH`.
2. Otherwise, use `$HOME/.local/bin/dgate` when it exists and is executable. This is the official installer's default location in non-root Linux and AgentHub sandboxes.
3. Otherwise, check `$HOME/bin/dgate`. If none of these locations exists, follow `getting-started.md`. Do not run an installer until the user explicitly approves installing software in the target environment.

In the examples below, replace `dgate` with the resolved absolute path when it is not available on `PATH`.

Start with:

```bash
dgate -v
dgate config show
```

Do not echo tokens from local configuration. Use `-o json` for remote business commands and read the structured status before consuming `data`.

## Identity and permissions

```bash
dgate acl role current -o json
dgate acl list --mine -o json
```

Use `role current` only for the platform role and administrator marker. Use `list --mine` for real instance-level data permissions.

## Metadata discovery

```bash
dgate meta catalog list -o json
dgate meta catalog search <keyword> -o json
dgate meta database list <catalogUuid> -o json
dgate meta database search <keyword> -o json
dgate meta table list <databaseUuid> -o json
dgate meta table columns --database-uuid <databaseUuid> --table <tableQualifiedName> -o json
dgate meta table indexes --database-uuid <databaseUuid> --table <tableQualifiedName> -o json
```

Use list and search filters to reduce candidates, then keep the exact returned identifiers. Continue every paginated command until `pagination.hasMore=false` when completeness matters.

## Data semantics

```bash
dgate wiki ask "<business question>" -o json
dgate wiki search "<query>" --wiki <wikiUuid> -o json
dgate wiki get <knowledgeUuid> --format markdown
```

Use `ask` when the correct table or business definition is unclear. Use `search` when `wikiUuid` is already known and direct retrieval is sufficient.

## Read-only execution

```bash
dgate exec --database-uuid <databaseUuid> "SELECT ... LIMIT 100" -o json
dgate exec --catalog-uuid <catalogUuid> "SHOW TABLES" -o json
```

Execute one bounded read-only statement. Do not use this Skill for mutations or DDL.

## Read-only control-plane inspection

```bash
dgate datasource list -o json
dgate datasource get <dataSourceUuid> -o json
dgate policy list -o json
dgate policy get <policyId> -o json
dgate guard mask-rule list -o json
dgate guard protected-column list -o json
dgate guard row-rule list -o json
```

For audit commands, inspect `dgate audit --help` and invoke only a documented read command; do not guess a subcommand. Avoid datasource write commands, metadata crawl, policy changes, guard batch-set/save, and Wiki feedback/edit/review/remove in this read-only Skill.

## Historical failure diagnosis

```bash
dgate trace list --command exec
dgate trace show <runIdOrRequestId>
dgate trace turn last --with-output -o json
```

Trace reads the existing local command ledger. Debug performs a new call and may expose raw protocol traffic, so do not substitute it for trace history.
