# Acceptance Criteria: alibabacloud-flink-python-coding

Apply every criterion relevant to the active workflow branch.

## Contents

- Version contract
- API path
- Source and sink contracts
- Credentials
- Dependencies and runtime files
- Documentation routing
- Deployment artifacts
- Validation evidence
- Cloud-operation boundary

## Version contract

### Correct

- Defaults a new job with no declared VVR version to VVR 11.8.
- For an existing job earlier than VVR 11.8, explains that the skill supports VVR 11.8 or later, recommends VVR 11.8, and finishes without implementation artifacts.
- Records VVR, base Flink/JDK, Python, local `ververica-flink`, and documentation versions independently.
- Uses Python 3.9, 3.10, or 3.11 and an exact local package version supported by direct evidence.

### Incorrect

- Infers the local package or documentation version from a VVR label.
- Implements against `/latest/`, an unresolved preview, an unsupported Python version, or a target earlier than VVR 11.8.

## API path

### Correct

```python
import pyflink.dataframe as pf
from pyflink.dataframe import col

result = source.filter(col("amount") > 0)
```

- Verifies DataFrame symbols against exact versioned ReadTheDocs pages reached from the DataFrame API index, and verifies multimodal operators against Alibaba Cloud operator documentation plus target-VVR availability evidence.
- Uses direct DataFrame methods first, expressions accepted by those methods second, and the smallest documented Table bridge only when required.
- Records the reason and location of each Table bridge and converts back through documented `pf.from_table(...)`.

### Incorrect

- Selects an API because it exists in another release, module, or memory rather than the target documentation.
- Passes an unsupported expression type to a DataFrame method or constructs `pf.DataFrame(table_result)`.

## Source and sink contracts

### Correct

- Preserves confirmed schemas, keys, nullability, precision, time semantics, changelog mode, startup behavior, and delivery expectations.
- Uses centralized, visibly labeled local examples when a source or sink detail is unavailable, with every replacement condition documented.

### Incorrect

- Presents an example topic, endpoint, table, schema, primary key, startup offset, or delivery mode as confirmed or deployment-ready.
- Changes a confirmed contract silently.

## Credentials

### Correct

- Uses a connector- or model-appropriate entry-point argument whose value is supplied through `${secret_values.<VARIABLE_NAME>}` in **Entry Point Main Arguments**.
- Tells the user to create the named variable under **Security > Variables** and keeps credential values out of source, README, logs, examples, git, and conversation text.

### Incorrect

- Embeds a credential value or `${secret_values.<VARIABLE_NAME>}` expression in Python source.
- Requests that the user paste AK/SK, passwords, API keys, or tokens into the conversation or a committed file.

## Dependencies and runtime files

### Correct

- Distinguishes local API packages from VVR runtime packages and checks the exact target's pre-installed package list.
- Pins every non-pre-installed distribution and records CPU, Python ABI, and glibc compatibility.
- Generates `scripts/build_dependencies.sh` with the `quay.io/pypa/manylinux_2_28_x86_64` Docker image only for a compatible x86-64 target.
- Maps every reachable file read to its source, consumer, local fixture, attachment mode, target path, and validation status.

### Incorrect

- Treats a successful local import as proof of target availability.
- Adds an unpinned package, silently selects Python, uses the build image for an incompatible target, or leaves target code bound to a workstation path.

## Documentation routing

### Correct

- Uses `https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job` for Python job development and pre-installed packages.
- Names `https://help.aliyun.com/en/flink/realtime-flink/api-reference` the **DataFrame API index**.
- Follows the **PyFlink DataFrame** link on the DataFrame API index to the exact versioned ReadTheDocs root, then opens category and symbol pages.
- Uses the multimodal operator index as an Alibaba Cloud documentation entry point rather than as a ReadTheDocs router.

### Incorrect

- Uses the obsolete Python job-development URL.
- Treats an index, category, synthesized version, or `/latest/` page as exact DataFrame symbol evidence, or expects the multimodal operator index to provide ReadTheDocs links.

## Deployment artifacts

### Correct

- Places new-project outputs directly in the project root and preserves an existing project's established layout.
- Includes source code and deployment documentation whose directory tree matches the filesystem.
- For modular code, generates and checks `scripts/package_code.sh`, preserves import paths in the code ZIP, and records a resolvable Entry Module.
- For non-pre-installed packages, includes exact pins and `scripts/build_dependencies.sh`; includes `deps.zip` only after a successful build with the documented Docker image.
- Maps code to Python File Path, `deps.zip` to Python Libraries, archives to Python Archives, and independent files or connector JARs to Additional Dependency Files.
- When DataFrame LLM functions are used or mentioned, points the README to Flink AI Service.

### Incorrect

- Returns only a prose summary, creates an extra delivery wrapper, omits source or README, leaves raw placeholders, or mixes code and dependency ZIPs.
- Claims a ZIP was built without successful build and ZIP evidence.

## Validation evidence

### Correct

- Records every applicable check as `passed`, `failed`, or `not run`, with command or fixture and supporting evidence.
- Compiles changed Python, runs repository checks, validates exact-version imports when available, and uses bounded fixtures.
- Separates local evidence from target VVR checks.

### Incorrect

- Collects an unbounded stream, reports a blocked check as passed, claims connector reachability without target evidence, or treats a local API import as VVR execution.

## Cloud-operation boundary

### Correct

The normal skill path edits and validates code, then produces upload-ready local artifacts. It invokes no Alibaba Cloud API and needs no observability block.

### Incorrect

Uploads files, mutates a workspace, creates or starts a deployment, or calls Alibaba Cloud APIs without a separate request and the added parameter, permission, observability, verification, and cleanup controls.

## Completion criterion

Acceptance passes only when every criterion applicable to the selected branch is satisfied and every exception has explicit evidence.
