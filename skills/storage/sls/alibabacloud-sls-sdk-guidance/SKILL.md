---
name: alibabacloud-sls-sdk-guidance
description: Provide Alibaba Cloud SLS / Aliyun Log SDK installation, quickstart, usage guidance, and SDK selection advice across languages. Use when users ask how to install or use SLS SDKs, choose an SDK for a scenario, write logs, consume logs, query logs, or integrate application logs with Producer, Consumer, or logging framework Appender libraries.
---

# Workflow

1. Read `references/route.md` first.
2. Identify the user's primary intent: install, write logs, consume logs, or query logs.
3. Pick exactly one scenario file from `references/scenarios/` unless the user explicitly asks for comparison across multiple scenarios.
4. Follow references from the scenario file to the relevant SDK `index.md`.
5. Read SDK-level `write-logs.md` or `consume-logs.md` only when the scenario points to it or the user asks for concrete code.
6. Do not scan unrelated SDK directories.
7. When recommending an SDK, explain why it fits and mention when it should not be used.
8. For version-sensitive installation commands, avoid inventing exact latest versions. Use package-manager commands that resolve latest versions, or use version placeholders for Maven/Gradle production examples.
