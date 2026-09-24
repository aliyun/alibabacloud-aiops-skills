# API Inquiry — Explain or Select

Answer API questions and comparisons using documentation or package source for the relevant VVR release.

1. Establish the version using [version selection](../product-contract.md). For a general question without a target, use the newest formal release and state it; ask when an existing job's compatibility depends on its version.
2. Read the relevant API documentation or source, following the [official entry points](../official-docs.md) beyond the skill's files. Use matching local `ververica-flink` source/docstrings if available; otherwise open ReadTheDocs documentation and linked source. Evidence already inspected in this conversation can be reused when its version and scope still match. This workflow does not require installing an environment.
3. Inspect the relevant [DataFrame capabilities](../dataframe-api.md) and symbols for every question, including AI/multimodal functions. For connector selection, also read the connector documentation. Resolve conflicting capability or limitation claims using [source precedence](../official-docs.md#source-precedence).
4. Once the inspected evidence supports the conclusion, lead with DataFrame API usage and a short example when useful. Use Table/DataStream when explicitly requested or when the selected version's DataFrame API cannot meet the need. Cite the page or package version and symbol that supports the answer, including any claimed limitation or workaround.

A missing keyword, missing skill reference, or failed documentation fetch leaves the question **unverified**, not unsupported. Try the linked API/source route; if the evidence remains unavailable, answer only the verified parts and state what still needs confirmation.

Ask for Python only when it changes the answer. Bring in [resolve](resolve-dependencies.md) or [prepare](prepare-deployment.md) if the user also requests that work; an explanation alone needs no job artifacts.
