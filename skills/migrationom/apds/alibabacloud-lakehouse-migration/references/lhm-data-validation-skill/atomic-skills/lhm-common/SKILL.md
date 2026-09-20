---
name: lhm-common
description: Shared foundation for LHM skills. Provides unified configuration management (data_validation_config.yaml), precondition checks (resource group / service agent / data sources / API connectivity), guided configuration (setup), and client building. All LHM business Skills should invoke the check subcommand to verify preconditions before execution. Also triggers when the user asks to configure LHM, e.g. "帮我配置 LHM" (help me configure LHM).
version: 1.0.0
---

# lhm-common — LHM Shared Skill Foundation

## Positioning

Shared infrastructure for all LHM skills, replacing the former `lhm-preflight-check` and `lhm-client-builder`.

Core capabilities:
1. **Centralized configuration**: AK/SK/Region/resource group/service agent/data sources are stored uniformly in `~/.lhm/data_validation_config.yaml`
2. **Standardized pre-checks**: each business Skill declares a profile, and preconditions are validated automatically before execution
3. **Human-friendly guidance**: the `setup` command walks the user through the full configuration step by step

## Runtime Environment

- Python venv: `~/.qoderwork/skills/data-validation-skill/.venv/bin/python`
- Dependency: `pyyaml`; the network layer requires the aliyun CLI + aliyun-cli-lhm plugin (request models are provided by the local `scripts/lhm_models.py`, no extra SDK install needed)
- Script path: `~/.qoderwork/skills/data-validation-skill/atomic-skills/lhm-common/scripts/run.py`

## Steps

### 1. First-Use Guided Setup

When the user asks for help configuring LHM (the Chinese trigger phrases are declared in the frontmatter description) or runs any LHM skill for the first time:

```bash
python run.py setup
```

The output contains a guided structure of 6 steps. Steps 1/2/4 have `prompt_fields` (ask the user and write the values in); steps 3/5 are console operations (`manual_step`); step 6 is automatic verification. For each step with `prompt_fields`, ask the user one by one and write the values with `setup-write`.

```bash
# Write the values provided by the user
python run.py setup-write '{"api.access_key_id":"LTAI...","api.access_key_secret":"xxx","api.region":"hangzhou"}'
```

Each step is written to data_validation_config.yaml immediately after completion, so exiting midway does not lose any filled-in content.

Guidance documents are loaded on demand:
- `guides/setup-overview.md` — first-time configuration overview
- `guides/resource-group-config.md` — detailed steps for resource group configuration
- `guides/agent-config.md` — detailed steps for service agent configuration
- `guides/data-source-config.md` — data source configuration guide

### 2. Pre-Execution Check

Before executing any business Skill, run:

```bash
python run.py check --profile data-validation
```

Check the `ready` field:
- `true` → the business Skill may proceed
- `false` → show the `fix_guide` of the corresponding `blocking_items` and guide the user to fix them

### 3. Build the Client

```bash
python run.py client              # read from data_validation_config.yaml
python run.py client --region singapore  # override region
```

### 4. Configuration Management

```bash
python run.py config list                              # list all configuration (AK masked)
python run.py config get api.region                    # read a field
python run.py config set api.region singapore          # set a field
python run.py config add-ds --alias mc --ds-id 123 --ds-name "订单库" --ds-type MaxCompute
python run.py config remove-ds --alias mc              # remove a data source
python run.py config show --alias mc                   # view data source details
```

## Profile Definitions

Each business Skill declares the profile it needs:

| Profile | Mandatory checks | Optional checks |
|---------|------------------|-----------------|
| `data-validation` | api_credentials, api_connectivity, resource_group, agent, data_sources | — |
| `sql-convert` | api_credentials, api_connectivity | resource_group |
| `schedule` | api_credentials, api_connectivity | resource_group, data_sources |

Check item implementations:
- `api_credentials` — verify that AK/SK exist in data_validation_config.yaml or environment variables
- `api_connectivity` — call `GetDataCheckTaskList(page_size=1)` to verify reachability
- `resource_group` — call `GetLhmDWResourceGroupStatus(region_id)` to query the status
- `agent` — call `GetLhmAgentStatus(agent_type=1)` to query the online status
- `data_sources` — currently pending_api; only verifies that data source definitions exist in the config file

## Pitfalls

- The `response.body.data` of `GetLhmDWResourceGroupStatus` and `GetLhmAgentStatus` is a **plain string** (not JSON); compare it directly
- Agent status is considered available only when it is `Online`; resource group status is considered healthy only when it is `Normal`
- The `check` command automatically updates the `resource_group.lhm_binding_status` and `agent.agent_status` caches in data_validation_config.yaml
- In the output of `config list`, access_key_secret is automatically masked (only the first 4 characters shown)
- The `data_sources` check item currently always returns `pending_api` (regardless of whether data sources are configured) and does not verify the real connectivity of data sources. Therefore `ready=true` does not mean the data sources are reachable — only that they are defined in the config file

## Verification

```bash
# 1. Verify the CLI is usable
python run.py config list

# 2. Verify the configuration is complete
python run.py check --profile data-validation

# 3. Verify client building
python run.py client
```
