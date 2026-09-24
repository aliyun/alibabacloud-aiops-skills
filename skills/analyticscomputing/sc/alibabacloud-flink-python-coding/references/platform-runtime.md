# VVR Deployment Runtime

Use these mappings when preparing the job README. Verify target-specific details in the [Python job guide](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job), [dependency guide](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/use-python-dependencies), and [deployment guide](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/create-a-deployment).

## Artifacts and console fields

| Artifact | Console field | Runtime behavior |
|---|---|---|
| Single `.py` or modular code ZIP | Python File Path | A ZIP also needs Entry Module, resolvable from its root |
| Third-party wheel or `deps.zip` | Python Libraries | Added to the Python worker import path |
| Custom Python environment or data archive | Python Archives | Extracted in the Python worker working directory |
| Independent file or custom connector JAR | Additional Dependency Files | Available under `/flink/usrlib` |

Record the deployment name/mode, exact engine version, entry file/module, arguments, and the fields selected by the artifacts. Apply the [execution-mode guidance](../SKILL.md#execution-mode) when selecting the deployment mode. Use clear placeholders for environment-specific values still to be supplied.

## Python runtime selection

VVR in this skill's supported range provides Python 3.9, 3.10, and 3.11. For the selected non-default interpreter, document both settings, for example:

```yaml
python.executable: python3.11
python.client.executable: python3.11
```

A custom environment uses the extracted archive's interpreter path instead. Verify its compatibility against the target VVR release.

## Credentials and service setup

Separate ordinary configuration from credentials in **Entry Point Main Arguments**. Use known values or plain placeholders for endpoints, regions, queue/topic names, paths, and other non-sensitive settings. Reserve `${secret_values.NAME}` for credentials such as passwords, tokens, and access keys; document their creation under **Security > Variables**.

For example, an MNS source's ordinary configuration and credentials can appear together:

```text
--mns-endpoint <mns-endpoint>
--mns-region <mns-region>
--mns-queue-name <mns-queue-name>
--access-key-id ${secret_values.OSS_ACCESS_KEY_ID}
--access-key-secret ${secret_values.OSS_ACCESS_KEY_SECRET}
```

Tell the user to replace the angle-bracket placeholders with their configuration. The job parses all arguments normally. Secret variable expressions belong in the console argument field; source and delivered files contain variable/argument names, not secret values.

For AI jobs, follow the [model access guidance](dataframe-api.md#ai-and-multimodal-capabilities) and document the selected service, model/task, and required setup.

## Deployment target

A Session cluster is intended for development and has different supported console features, including no Additional Dependency Files. Check the deployment guide before selecting it for a job that needs attachments.

Preserve source/sink semantics and required runtime settings in the handoff. Manual deployment instructions or a job-submission skill can use this same mapping.
