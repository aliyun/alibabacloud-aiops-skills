# Related Commands

This skill uses local development and artifact-preparation commands; it does not need Aliyun CLI because the core workflow calls no Alibaba Cloud API. Select commands only after the target contract and project layout resolve their placeholders.

| Purpose | Command | Trigger |
|---|---|---|
| Create an isolated environment | `python -m venv .venv` | The repository has no environment workflow |
| Install the exact API package | `python -m pip install "ververica-flink==<confirmed-version>"` | The exact version is confirmed and installation is approved |
| Compile changed Python | `python -m py_compile <changed-python-file>` | Every changed Python file |
| Run repository tests | `python -m pytest` | Pytest tests exist |
| Syntax-check a generated script | `bash -n <script-path>` | Before project-side script execution |
| Package modular code | `bash scripts/package_code.sh <source-root> <code-archive> <entry-module>` | The artifact list includes modular code |
| Build third-party dependencies | `bash scripts/build_dependencies.sh <confirmed-python-version> <requirements-file> <dependency-archive>` | The dependency contract requires `deps.zip` and the target is compatible |
| Test a ZIP | `python -m zipfile -t <archive.zip>` | A ZIP build succeeds |
| List a ZIP | `python -m zipfile -l <archive.zip>` | Verify code or dependency root layout |

Keep repository-native commands when they are stronger than the generic entries above, and record the command actually run in validation evidence.
