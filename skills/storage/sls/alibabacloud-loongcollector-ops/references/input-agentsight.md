# `input_agentsight` plugin (collector knowledge)

Authoritative schema and runtime semantics for LoongCollector AgentSight. Agentloop confirm-access names are product-fixed (`runtime-ebpf-agentsight-config` -> `ebpf-event`).

This is **not** OBI and **not** OTLP Metrics/Traces.

## Provenance (verified 2026-08-20)

| Source | Rev / URL | What to trust |
|---|---|---|
| `loongcollector-inner` `origin/main` (repo default; newer than `origin/master`) | `e7d61e027` 2026-08-13; plugin doc merged `bb7d8c096` 2026-08-12 | Code + `docs/cn/plugins/input/native/input_agentsight.md` |
| `loongcollector-inner` `origin/master` | `8bcc41283` 2026-07-31 | Same builtins; **no** `RawHttpsFallback` |
| Open-source plugin doc | https://github.com/alibaba/loongcollector/blob/main/docs/cn/plugins/input/native/input_agentsight.md | Matches inner `main` |
| SLS console help | https://help.aliyun.com/zh/sls/collect-ai-agent-observability-agentsight-logs | Product packaging, kernel, SSL compatibility |
| Builtin lists | `core/ebpf/plugin/agentsight/AgentsightManager.cpp` `GetBuiltinHttpsAllowRules` / `GetBuiltinCmdlineAllowRules` | **Code wins** if docs disagree on counts |

`origin/HEAD` → `origin/main`. Do not treat stale `origin/master` as latest.

## Version and host gates

| Gate | Value | Authority |
|---|---|---|
| Cloud / this skill | LoongCollector **`>= 3.3.9`** | SLS help: "not below v3.3.9" |
| Plugin in-tree doc | `>= 3.3.4` | in-tree `input_agentsight.md` still says 3.3.4 (first source merge) |
| Kernel | Linux **`>= 5.10`** | SLS help; verified Alibaba Cloud Linux 3 / Ubuntu 22.04 / 24.04 |
| OS | Linux host eBPF; not Windows | plugin + help |
| `RawHttpsFallback` | inner **main after 2026-08-12**; `libagentsight >= 0.9.0`; **not** in 3.3.9 GA help | inner `main` |

Unknown collector version → ask; never assume 3.x. Below 3.3.9 on a cloud Agentloop job → block and tell the user to upgrade (do not improvise host install).

## ProbeConfig schema (pipeline JSON)

Keys are PascalCase. Legacy `CmdlineRules` / `DomainRules` / `DomainWhitelist` / `gen_ai.agent.name` are **gone** (breaking, PR #2560 / #2567). Do not emit them.

| Key | Type | Default | Notes |
|---|---|---|---|
| `Verbose` | uint 0/1 | omit (`0`) | eBPF debug log |
| `LogPath` | string | omit | eBPF log path |
| `CmdlineWhitelist` | `[{AgentType, Args}]` | inject 9 builtins if **both** cmdline lists omitted | `[]` illegal |
| `CmdlineBlacklist` | `[[glob,…]]` | none | higher priority than whitelist |
| `Https` | string[] | inject **7** builtins if omitted/empty | attach filter only — see below |
| `Http` | string[] | `[]` (plaintext off) | `:port` / `IP` / `IP:port` / domain |
| `EventStreamFormat` | bool | `true` | two logs per LLM call |
| `MessageDeltaOnly` | bool | `true` | no full `gen_ai.input.messages` |
| `RawHttpsFallback` | bool | `false` | **omit unless user explicitly wants it** |

Empty `ProbeConfig: {}` (or omitting the object) → collector injects cmdline + HTTPS builtins. Filling **any** row of a list **replaces that list entirely** (no merge). If the user still needs a builtin host, they must write it back.

### Builtin `CmdlineWhitelist` (9)

| AgentType | Args |
|---|---|
| `hermes` | `hermes*` |
| `hermes` | `*python*`, `*hermes*` |
| `hermes` | `*python*`, `-m`, `*hermes*` |
| `cosh` | `node*`, `*/usr/bin/co*` |
| `cosh` | `node*`, `*/usr/bin/cosh*` |
| `cosh` | `node*`, `*/usr/bin/copliot*` |
| `cosh` | `node*`, `*copilot-shell*` |
| `openclaw` | `*openclaw-gatewa*` |
| `openclaw` | `node*`, `*openclaw*` |

Official help also names Claude Code / QwenPaw / LangChain and others as *supported agents*, but they are **not** extra builtin cmdline rows. Match them with user `CmdlineWhitelist` or via `Https` attach.

### Builtin `Https` (7 — code)

`api.openai.com`, `api.anthropic.com`, `dashscope.aliyuncs.com`, `dashscope-intl.aliyuncs.com`, `dashscope-us.aliyuncs.com`, `coding.dashscope.aliyuncs.com`, `*.maas.aliyuncs.com`

`*.maas.aliyuncs.com` covers workspace / trial / token-plan hosts (`*.{region}.maas.aliyuncs.com`). Glob `*` crosses `.`. Wildcard is for SNI attach; TCP/IP process-discovery skips DNS of wildcards.

Inner `main` heading still says "default Https (6 entries)" while the table and C++ vector have 7. **Trust the vector.**

## Attach vs report (easy to get wrong)

HTTPS **process attach** order:

1. `CmdlineBlacklist` hit → skip
2. else `CmdlineWhitelist` hit → attach
3. else process talks to an `Https` host → attach
4. else skip

`Http` is a **separate destination whitelist** for plaintext; empty = off. Independent of cmdline.

**`Https` does not filter what an attached process reports.** Once attached (cmdline *or* domain), all of that process's unparseable HTTPS can become raw events if `RawHttpsFallback` is on. Narrowing `Https` only reduces *how many processes* get the SSL probe. Scope control: blacklist processes, or leave `RawHttpsFallback` off (Agentloop default).

## `RawHttpsFallback` (main only; default off)

When `true` and `libagentsight >= 0.9.0`, traffic that cannot be parsed as LLM semantics is emitted as `event.name=http.request` / `http.response` (own `event.id`, pair via `http.exchange.id`). Mutually exclusive with `gen_ai.*` for the same exchange. Raw **body is not masked**. Request headers are a tiny allowlist (`content-type`, `content-length`, `traceparent`); `Authorization` is dropped. Binary bodies can be silently UTF-8-lossy.

Agentloop empty form **must not** set this. Older `libagentsight` logs a warning and stays off.

Raw fields use `agent.type` (no `gen_ai.` prefix). LLM logs keep `gen_ai.agent.type`. Same value, different key — do not rename.

## LLM field contract (`EventStreamFormat: true` default)

- `event.id` is **per log line** (request and response differ). Official help text that says they share one `event.id` is **wrong**; plugin doc + samples use two UUIDs. Pair via `gen_ai.session.id` / `gen_ai.turn.id` / `gen_ai.step.id`.
- Keep dotted names. Query with double quotes. Do not `processor_rename`.
- Extra fields on inner `main` LLM lines: `cmdline`, `container.id`.

U6 example:

```text
* | select __time__, "event.name", "gen_ai.agent.type", "gen_ai.session.id" limit 5
```

## Official help vs this skill

| Topic | Help / console | This skill |
|---|---|---|
| Config JSON | sometimes `"type"` + `"detail": {ProbeConfig}` (classic) | Pipeline: `"Type"` + `ProbeConfig` on the input object |
| Min version | 3.3.9 + kernel 5.10 | same for cloud jobs |
| SSL attach | Node/Python/symbol-exported OK; strip+static OpenSSL = limited; Codex CLI strip-static = **unsupported** | tell the user in prose; no host SSH |
| `event.id` | "request and response share one ID" | **do not copy**; each line has its own `event.id` |

## SSL / eBPF attach (help technical appendix)

| Binary | HTTPS capture |
|---|---|
| Node/Python, or keeps SSL symbols | yes (`SSL_read` / `SSL_write`) |
| stripped, static OpenSSL, bytecode match | limited |
| stripped static, no symbols, no bytecode match (e.g. official Codex CLI) | no |

Kernel check is host-side: ask the user to confirm `uname -r` ≥ 5.10 in prose — this skill does not SSH.
