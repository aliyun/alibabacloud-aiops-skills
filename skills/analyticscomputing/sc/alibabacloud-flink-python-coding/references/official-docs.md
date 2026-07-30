# Official Documentation Routing

Use live primary sources to build the exact-version evidence set before selecting an API or platform behavior.

## Record evidence

For each result-affecting claim, record the claim, target version, direct URL, and what the page proves. Index and overview pages route the search; the linked versioned symbol or behavior page supplies the evidence. Mark conflicts and unresolved claims explicitly.

The evidence set is complete only for the active workflow branch. Read-only work needs evidence for the requested answer or finding; implementation additionally needs evidence for every selected API, connector behavior, dependency rule, runtime-file path, and deployment field.

## Resolve versions

- Treat the VVR release, base Flink/JDK identity, Python version, local `ververica-flink` package, and documentation version as separate values.
- Confirm the target VVR and its supported Python runtime in the [Python job development documentation](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job) and target release notes.
- Use Python 3.9, 3.10, or 3.11; record one exact target version.
- Resolve an exact `ververica-flink` version from official package or release evidence. A VVR label alone does not prove the local package version.
- For DataFrame APIs, use the target release's versioned ReadTheDocs pages; `/latest/`, a synthesized version, or a category page is not exact-version evidence.

Start release-note routing at `https://help.aliyun.com/zh/flink/realtime-flink/product-overview/`, then select the target VVR release.

## Route Python APIs

Use these Alibaba Cloud pages as the only entry points to the recommended Python API surface:

- **DataFrame API index:** `https://help.aliyun.com/en/flink/realtime-flink/api-reference`
- **Multimodal operator index:** `https://help.aliyun.com/zh/flink/realtime-flink/multimodal-operator`

For DataFrame APIs, open the **DataFrame API index**, follow its **PyFlink DataFrame** link to the root of the versioned ReadTheDocs API, then navigate to the category and exact symbol page.

For multimodal operators, use the **Multimodal operator index** and its Alibaba Cloud documentation. Confirm availability for the target VVR through the operator and product documentation. The multimodal index is not a ReadTheDocs router.

DataFrame APIs and multimodal operators listed by these two entry pages, plus `pyflink.table.expressions` accepted by documented DataFrame methods, form the recommended surface.

Use these pages for examples after the exact API has been resolved:

- DataFrame quickstart: `https://help.aliyun.com/zh/flink/realtime-flink/quickstart`
- DataFrame feature overview: `https://help.aliyun.com/zh/flink/realtime-flink/overview`
- DataFrame multimodal tutorial: `https://help.aliyun.com/zh/flink/realtime-flink/dataframe-api`

## Resolve connector contracts

Start from the [supported connector index](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/connectors), then open the direct page for each selected connector and format. Record the built-in identifier, schema mapping, authentication reference, startup behavior, and delivery semantics. Keep local example resource identifiers and schemas visibly labeled for replacement.

## Route platform behavior

- Python dependency and runtime-file handling: `https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/use-python-dependencies`
- Python job development and pre-installed packages: `https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job`
- Create a deployment: `https://help.aliyun.com/zh/flink/realtime-flink/user-guide/create-a-deployment`

Use product documentation for VVR availability, built-in packages, connector packaging, attachment fields, runtime paths, and deployment behavior.

## Completion criterion

Complete documentation resolution when every version required by the branch is explicit; every DataFrame symbol has direct exact-version ReadTheDocs evidence; every multimodal operator has direct Alibaba Cloud documentation and target-VVR availability evidence; every platform behavior has direct product evidence; and every conflict or unresolved claim is recorded.
