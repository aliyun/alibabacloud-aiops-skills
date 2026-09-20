# DTS-AI Authentication

## API key lookup order

Resolve the API key in this order:

1. The `DTS_AI_API_KEY` environment variable in the current process.
2. `~/.aliyun-dts/dts-ai/credentials.json`.

Never read or modify a shell startup file. Never print, log, or separately persist the decoded API key.

## Credential file requirements

Accept only this v1 JSON object:

```json
{"schema_version":1,"service":"aliyun-dts-ai","api_key":"<base64-api-key>"}
```

`api_key` is standard Base64 of the key's UTF-8 bytes. Base64 is a reversible encoding, not encryption. Never add encoding-specific field names or metadata.

Reject a credential file if any of the following applies: malformed JSON; duplicate or unknown fields; an unsupported `schema_version` or `service` value; an empty `api_key` or non-standard Base64; invalid UTF-8, a BOM, or control characters; a file larger than 16 KiB; a symlink, Windows reparse point, non-regular file, or file not owned by the current user.

When writing, first use a temporary file in the same directory, then replace the credential file atomically. Store no API key in a Skill directory, workspace, saved output, job record, URL, command argument, page source, command output, error message, or log.

## Interactive setup

`dtscli ai setup` starts a temporary server on a random `127.0.0.1` port and opens the system default browser. Use `--language zh` for a Chinese conversation and `--language en` otherwise.

Require:

- a random session path and CSRF token;
- validation of the exact Host header and same-origin evidence from the Origin or Referer header;
- enforced limits on form size and field count;
- a password input;
- disabled request logging, caching, framing, external resources, and unnecessary browser permissions;
- server termination after one successful save, cancellation, or a timeout, which defaults to five minutes and is adjustable with `--page-timeout`, using a positive number of seconds or a duration such as `5m`.

The success page may state only that configuration is complete. It must not show the API key or credential path.

## Agent restrictions

Never:

- display or reveal the session URL;
- use browser automation to open or inspect the page;
- ask the user to provide the key through chat, terminal input, a command argument, or a tool result;
- add a fallback that accepts the key through terminal input;
- read, write, replace, or remove API key assignments in shell startup files.

If the system browser cannot open, the command prints the session URL on standard error. Never relay that URL into the conversation; tell the user to run `dtscli ai setup` themselves in a terminal and complete the page it opens.

Direct the user to the [Alibaba Cloud RAM API Key console](https://ram.console.aliyun.com/profile/api-keys) to create a key for "Data Transmission Service / DTS".

<a id="service-configuration"></a>
## Service configuration

| Setting | Required value |
| --- | --- |
| Endpoint | `dtsai.cn-beijing.aliyuncs.com` |
| API version | `2026-04-01` |
| Region | `cn-beijing` |
