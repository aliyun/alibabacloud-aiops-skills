# Installation and configuration

## 1. Aliyun CLI and SLS plugin

Follow the [official installation instructions](https://help.aliyun.com/zh/cli/) for the operating system and add `aliyun` to PATH. Use a user-writable installation directory if the default location is not writable.

Check the versions and the help for the command required by the selected workflow, for example:

```bash
aliyun version
aliyun sls version
aliyun sls get-index --help
```

Install a missing plugin, or update an existing plugin when a required command or option is unavailable:

```bash
# Missing plugin
aliyun plugin install --names sls

# Existing plugin lacks a required command or option
aliyun plugin update --name sls
```

After installation or an update, check the required command's help again.

## 2. CLI authentication

Use the environment's configured authentication. Pass `--profile` only where the workflow supports it and the user has specified one. Keep the default profile, region and endpoint unchanged.

For authentication setup, follow the [official credential instructions](https://help.aliyun.com/zh/cli/configure-credentials/) for the selected mode.

Keep credential values out of commands, output and conversations. For credential environment checks, report only whether explicitly required variable names are set; never dump the environment or print credential values. Do not dump credential files or run `aliyun configure get` for diagnosis.

## 3. Troubleshooting

| Symptom | Check |
| --- | --- |
| `aliyun` not found | Installation directory and PATH |
| SLS command or option unavailable | SLS plugin and the required command's help |
| Invalid or expired credentials | The CLI authentication used for the failed request |
| Authorization denied | The reported action/resource and [RAM permissions](ram-policies.md) |

## 4. Python script prerequisites

Bundled scripts require Python 3.10+; check with `python3 --version`. `chat.py` uses the standard library and Aliyun CLI. `export_query_evidence.py` uses only the standard library. Neither script requires third-party Python packages.

## 5. model_qa.py dependencies

`model_qa.py` and its `_model_qa/` implementation require the packages in [requirements.txt](../scripts/requirements.txt). Package versions are maintained in that file.

Use the same interpreter and environment for installation and execution. Replace `<skill-dir>` with this Skill's absolute directory; if using a virtual environment, use its Python interpreter for these commands:

```bash
python3 -m pip install -r "<skill-dir>/scripts/requirements.txt"
python3 -m pip check
python3 "<skill-dir>/scripts/model_qa.py" --help
```

This entry point uses the Alibaba Cloud Credentials SDK default chain, which may select a different identity from Aliyun CLI. `aliyun configure list` does not verify the SDK's identity or permissions.

For missing modules, check the interpreter and its installed requirements. For authentication failures, check the credential provider used by this entry point.
