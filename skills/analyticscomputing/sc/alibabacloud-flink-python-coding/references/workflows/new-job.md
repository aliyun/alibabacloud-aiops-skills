# New Job — Write

Create a VVR Python job, its needed deployment artifacts, and a README explaining deployment.

## Establish the target and spec

1. Confirm VVR and Python using [version selection](../product-contract.md). For an unspecified new-job target, propose the latest formal VVR release and a supported Python version.
2. Locate or fetch the target version's [API source](../product-contract.md#obtain-api-source).
3. Establish the requested inputs, outputs, transformations, and relevant processing semantics. User-provided requirements count as confirmation; ask about gaps that change the intended behavior, such as an unspecified source or sink system. Parameterize deployment-specific values such as endpoints and credentials.

The agent chooses technical implementation details from the confirmed requirements and version evidence.

## Design and implement

- **Source/sink:** use the [connector access routes and capability index](../dataframe-api.md#source-and-sink-selection) to select a VVR connector and its dedicated, generic, or catalog-table entry point. Verify capabilities in connector documentation and the call in the selected package. Select source reading semantics and [execution mode](../../SKILL.md#execution-mode) separately.
- **Transformations:** inspect the selected `ververica-flink` code and docstrings, including the Expression API used by DataFrame columns, to establish scope. Apply [DataFrame-first selection](../dataframe-api.md), including AI and multimodal built-ins, with Table/DataStream fallback where needed.
- **UDFs and dependencies:** use [resolve](resolve-dependencies.md) for callbacks, third-party packages, runtime files, or custom connector JARs.
- **Code:** use the [recommended project layout](../project-layout.md), keeping source, transformation, and sink logic understandable.

## Check and deliver

Before delivery, read and follow [the local verification method](../verification-method.md), including running Pyright and reviewing its diagnostics.

Then [prepare deployment](prepare-deployment.md). Before writing the README, read and apply the [README requirements](../handoff-deliverables.md#write-the-readme). Deliver source, required artifacts or reproducible build scripts for blocked builds, and the README with manual deployment instructions and the information needed by a job-submission skill.

State any unresolved deployment values and checks requiring VVR. Handoff includes the Pyright command, result, and diagnostic review, or the concrete reason it could not run. The job is ready when its requested behavior is implemented, verification outcomes are reported, and the README matches the delivered artifacts; a clean Pyright result is not required.
