# Existing Job — Modify or Review

Use this workflow for changes to an existing job and for reviewing its implementation.

## Establish the existing target

Read the relevant code and configuration to determine VVR and Python; ask for missing versions using [version selection](../product-contract.md). Locate or fetch the matching [API source](../product-contract.md#obtain-api-source).

Identify the requested change or review scope, including affected schemas, sources/sinks, dependencies, and deployment settings. Preserve the job's API architecture and project layout; API migration requires a user request.

## Modify or review against VVR

Inspect the selected package's code/docstrings for the behavior under consideration. Read the specific [connector documentation](../official-docs.md) when a source/sink choice, option, or behavior is affected.

For new or substantially rewritten logic, consider [DataFrame capabilities](../dataframe-api.md) within the existing architecture. Make changes driven by the requested behavior, accounting for compatibility with the surrounding job.

Use [resolve](resolve-dependencies.md) for affected callbacks, imports, runtime files, and custom connector JARs. Retain unrelated dependency and deployment configuration.

## Deliver

- **Modify:** run [local checks](../verification-method.md), then [prepare](prepare-deployment.md) the affected artifacts and deployment instructions. Explain the behavior change and remaining VVR checks.
- **Review:** report actionable findings with code locations and supporting API/product evidence. An ordinary review produces findings; implement fixes when requested.
