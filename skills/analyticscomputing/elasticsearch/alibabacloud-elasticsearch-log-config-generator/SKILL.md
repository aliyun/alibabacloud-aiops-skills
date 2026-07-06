---
name: alibabacloud-elasticsearch-log-config-generator
description: >
  Use when the user needs to generate a log collection configuration file
  (OpenTelemetry Collector or Elastic Beats / Filebeat) that writes logs to
  Alibaba Cloud Elasticsearch or self-managed Elasticsearch. Covers file logs,
  log API ingestion (OTLP / HTTP webhook), and Kafka log topics. Also matches natural requests such as: write a filebeat.yml, generate
  an otelcol config, send logs to ES, collect nginx or Java application logs to
  Elasticsearch, or sync Kafka logs to ES. Always output one configuration file
  targeting Elasticsearch; never mix technology stacks or emit non-ES outputs.
license: Apache-2.0
compatibility: >
  Works with cloud-hosted or self-managed Elasticsearch. ES 8.12+ is
  recommended; OpenTelemetry mapping mode otel is recommended on ES 8.16+.
  Requires local otelcol-contrib or filebeat for configuration validation and
  runtime execution. This skill does not require online APIs; all references
  live under references/ and should be loaded on demand.
metadata:
  domain: aiops
  category: database
  product: alibabacloud-elasticsearch
  owner: alibabacloud-elasticsearch-team
  contact: alibabacloud-elasticsearch-skills@alibaba-inc.com
---

# Log Collection Configuration Generator (Elasticsearch)

## Scope

This skill generates exactly **one** valid configuration file that collects log data and sends it to **Elasticsearch**. It supports two technology stacks, and each request must choose exactly one:

- **OpenTelemetry Collector** (`otelcol-contrib`) - use `filelogreceiver`, `otlpreceiver`, or `kafkareceiver` with `elasticsearchexporter`.
- **Elastic Beats / Filebeat** - use `filestream`, `kafka`, or `http_endpoint` input with `output.elasticsearch`.

### Hard Constraints

1. **Generate only one configuration per request.** Do not concatenate or batch multiple configurations.
2. **Use exactly one technology stack.** Never mix OpenTelemetry components and Filebeat sections in the same file.
3. **Confirm before generating.** Do not generate YAML until the user has answered the Step 1 technology stack confirmation question in a separate reply.
4. **The output must be Elasticsearch.** Never use Kafka, S3, Logstash-only, files, or any other non-Elasticsearch destination as the final output.
5. **Logs only.** Inputs must be log-shaped sources: files, log webhooks, or Kafka topics that contain logs. If the user asks for a clearly different non-log input, refuse and explain why.
6. **No Syslog or Fluent forward input sources.** Do not generate collector or Filebeat listener configurations for Syslog or Fluent forward protocols. If the user asks for Syslog or Fluent forward as the source, refuse and ask them to choose file, OTLP, HTTP webhook, or Kafka log ingestion instead.
7. **Use local knowledge first.** Authoritative references live in the `references/` directory next to this `SKILL.md`. When a component option is covered locally, do not search the web; read the matching file under `references/`.
8. **Keep the design minimal.** Generate only fields requested by the user or required for the file to load. For common but optional features such as batching, retries, or ILM, recommend them and wait for explicit user confirmation before adding them.
9. **Never inline secrets.** Reference all secrets through `${env:VAR}` for OTel or `${VAR}` for Filebeat.

## Local References (Prefer Over Web Search)

Before writing YAML, read the matching file under `references/` to verify field names and defaults. The list below is complete. If the required option is not covered, ask the user before writing it.

### Security And RAM Permissions

- `references/ram-policies.md` - declares `required_permissions` for Alibaba Cloud RAM review.

### OpenTelemetry Collector - `references/opentelemetry/`

Components:
- `01-configuration-basics.md` - top-level structure, pipelines, environment variables, TLS.
- `02-filelogreceiver.md` - file tailing: include/exclude, multiline, operators, storage.
- `03-elasticsearchexporter.md` - `endpoint`/`endpoints`/`cloudid`, authentication, mapping mode, index, sending_queue.
- `04-kafkareceiver.md` - Kafka log ingestion, SASL, encoding.
- `05-otlpreceiver.md` - OTLP gRPC/HTTP log endpoints.
- `06-batchprocessor.md` - batching.
- `07-attributesprocessor.md` - add/delete/mask/extract attributes, log filtering.
- `08-resourcedetectionprocessor.md` - host, cloud, and k8s metadata.
- `09-transformprocessor.md` - OTTL transforms, including setting `elastic.mapping.mode`.
- `12-filestorage-extension.md` - persistent offsets and queues.

Transitive references used by the components above and already localized under hard constraint #5:
- `13-confighttp.md` - shared HTTP client/server configuration: compression algorithms gzip/zstd/snappy/zlib/deflate/lz4, `compression_params.level`, headers, timeouts, keep-alive, CORS, maximum body size. Used by `elasticsearchexporter` and `otlpreceiver/http`.
- `14-configtls.md` - TLS settings: `ca_file`, `cert_file`, `key_file`, `min_version`, `insecure_skip_verify`, mTLS `client_ca_file`, TPM. Used by `confighttp` and `configgrpc`.
- `15-configauth.md` - authentication extension wiring with `auth.authenticator: <ext-name>` and common client/server authentication extensions.
- `16-configgrpc.md` - gRPC client/server settings: `max_recv_msg_size_mib`, keepalive, `compression`, `balancer_name`. Used by `otlpreceiver/grpc`.
- `17-exporterhelper.md` - `sending_queue`, including persistent queues with `storage`, `retry_on_failure`, `timeout`, and batcher. Inherited by `elasticsearchexporter`.
- `18-ottl-overview.md` - OpenTelemetry Transformation Language (OTTL) overview, statements, and contexts. Used by `transformprocessor` and `filterprocessor`.
- `19-ottl-functions.md` - OTTL syntax and the full editor/converter catalog: `set`, `replace_pattern`, `IsMatch`, `ParseJSON`, and more.
- `20-ottl-log-paths.md` - `ottllog` context paths such as `log.body`, `log.severity_number`, attributes, and `SEVERITY_NUMBER_*` enums.
- `21-stanza-operators-overview.md` - operator catalog and shared fields. Used in the `operators:` block of `filelogreceiver`.
- `22-stanza-json_parser.md` - JSON parser operator, including embedded `timestamp:` and `severity:`.
- `23-stanza-regex_parser.md` - regex parser with named captures.
- `24-stanza-recombine.md` - multiline recombination for stack traces and records with date prefixes.
- `25-stanza-timestamp.md` - strptime, gotime, epoch layouts, and timezone handling.
- `26-stanza-severity.md` - severity tokens and mapping syntax.
- `36-stanza-key_value_parser.md` - key-value parser operator: `delimiter`, `pair_delimiter`.
- `37-stanza-csv_parser.md` - CSV parser with static or dynamic headers, `lazy_quotes`, and `ignore_quotes`.
- `38-stanza-container.md` - container runtime parser: auto, docker, crio, containerd; extracts K8s metadata from file paths.
- `39-resourcedetection-detectors.md` - option tables for detectors such as env, ec2, eks, aks, k8snode, kubeadm, gcp, azure, docker, openshift, and heroku; companion to `08-resourcedetectionprocessor.md`.
- `40-auth-extensions.md` - `basicauth`, `bearertokenauth`, and `headers_setter` extensions, wired through `15-configauth.md`.

Common processors and connectors to load only when the user asks for the related capability:
- `27-memorylimiterprocessor.md` - `memory_limiter`; must be first in every pipeline. Covers `check_interval`, `limit_mib`, `spike_limit_mib`, and soft/hard limit behavior.
- `28-filterprocessor.md` - drop logs by OTTL conditions: `log_conditions`, `error_mode`, contexts.
- `29-k8sattributesprocessor.md` - enrich logs with K8s pod, namespace, and node metadata: `auth_type`, `passthrough`, `extract.metadata`, `pod_association`; includes RBAC snippets.
- `30-redactionprocessor.md` - allow-listed fields plus regex masking or hashing: `allowed_keys`, `blocked_values`, `hash_function`.
- `31-resourceprocessor.md` - lightweight resource attribute operations: INSERT/UPDATE/UPSERT/DELETE/HASH/EXTRACT, `from_attribute`, `from_context`.
- `32-groupbyattrsprocessor.md` - regroup log records by matching Resource attributes with `keys`; an empty list compacts records.
- `33-logdedupprocessor.md` - merge duplicate logs within a window: `interval`, `log_count_attribute`, `conditions`, `include_fields`/`exclude_fields`.
- `34-routingconnector.md` - route to multiple downstream pipelines. This is a connector, not a processor, and replaces the deprecated `routingprocessor`.

### Filebeat - `references/beats/`

Components:
- `01-filebeat-configuration-overview.md` - top-level layout and validation commands.
- `02-input-filestream.md` - modern file input: id, paths, parsers, file_identity.
- `03-input-kafka.md` - Kafka input.
- `04-input-http_endpoint.md` - HTTP webhook input.
- `05-output-elasticsearch.md` - ES output, ILM interaction, conditional indexes, preset, conditional `pipelines:` mapping.
- `06-processors.md` - overview, ordering, `when:` filters, common processor catalog.
- `07-ssl.md` - TLS / mTLS.
- `08-ilm.md` - ILM policy management.
- `09-template.md` - index templates.
- `14-filebeat-general-settings.md` - top-level settings: `name`, `tags`, `fields`, `fields_under_root`, `processors`, `max_procs`, `timestamp.precision`.

Processors, deep reference:
- `13-filebeat-processors-detail.md` - option tables for the most common processors: `add_host_metadata`, `add_cloud_metadata`, `add_kubernetes_metadata` with RBAC, `add_docker_metadata`, `decode_json_fields`, `dissect` with tokenizer modifiers, `timestamp` with Go layouts, `fingerprint`, `script`, `drop_event`, and the field modification family: `add_fields`, `drop_fields`, `rename`, `copy_fields`, `convert`, `truncate_fields`, `urldecode`, `replace`, `extract_array`.
- `15-filebeat-processors-extra.md` - `community_id`, `decode_xml`, `decode_cef`, `decompress_gzip_field`, `registered_domain`, `append`, `move_fields`, `add_observer_metadata` off-host.

Filestream parsers to load when `parsers:` is needed under `02-input-filestream.md`:
- `16-filestream-parsers.md` - `multiline` with pattern / count / while_pattern, `ndjson`, `container` with auto / docker / cri, and `include_message`; includes combined stack examples.

Transitive references:
- `11-conditions.md` - processor `when:` / `if:` condition syntax: `equals`, `contains`, `regexp`, `range`, `network`, `has_fields`, `or`/`and`/`not`.
- `12-internal-queue.md` - `queue.mem` default and `queue.disk` settings, capacity tuning knobs.
- `17-setup-and-monitoring.md` - `setup.kibana`, `logging.*` including file rotation and systemd journald defaults, `monitoring.*` internal collection, and `http.*` status endpoints.

### Templates - `assets/templates/`

When a template matches the user's requested input, prefer modifying that template instead of writing from scratch:
- `otel-filelog-to-es.yaml`
- `otel-kafka-to-es.yaml`
- `otel-otlp-to-es.yaml`
- `filebeat-filestream-to-es.yaml`
- `filebeat-kafka-to-es.yaml`
- `filebeat-http_endpoint-to-es.yaml`

## Required Workflow

Execute the following steps **in order**. Do not skip steps. If any required parameter is unknown at a step, ask the user explicitly at that step.

### Step 1 - Choose The Technology Stack

Ask the user:

> Which collection configuration do you want to generate? (1) OpenTelemetry Collector  (2) Elastic Filebeat. Choose exactly one; this request will produce one configuration file.

Wait for an explicit answer in a separate user reply. Even if the initial user request names Filebeat, OpenTelemetry, filebeat.yml, otelcol, or a stack-specific input, do not treat that as the Step 1 confirmation.

Do not generate YAML in the same response that asks for the technology stack confirmation. Stop after the question above unless the current conversation already contains a direct answer to that confirmation question from an earlier turn.

### Step 2 - Determine The Log Input Source

Ask for the applicable input. Allowed log inputs by stack:

| Technology stack | Allowed inputs |
|---|---|
| OpenTelemetry | `filelog` (file), `otlp` (gRPC/HTTP log API), `kafka` (log topic) |
| Filebeat | `filestream` (file), `kafka` (log topic), `http_endpoint` (webhook) |

If the user asks for another type, such as database input, prometheus metrics, or vmware events, refuse and explain that it is outside this skill's log collection scope.

Collect the minimum required fields:
- **Files**: absolute glob path; whether to backfill existing content (`start_at: beginning` / first-start behavior); multiline pattern if needed.
- **OTLP**: listen address and port; whether TLS or an authentication extension is required.
- **Kafka**: brokers, topic(s), protocol_version, group_id, authentication with SASL mechanism and credentials, TLS.
- **HTTP webhook**: listen port, URL path, authentication with basic / shared header / HMAC, TLS.

### Step 3 - Determine The Elasticsearch Destination

Required fields:
- Connection - choose exactly one:
  - OpenTelemetry: `endpoint` / `endpoints` / `cloudid`.
  - Filebeat: `hosts` URL list.
- Authentication - choose exactly one: basic auth with `user`/`password` **or** API key with `api_key`.
- TLS - whether the endpoint is HTTPS, which CA file is trusted, or whether verification should be skipped with a warning.
- Index / data stream:
  - OpenTelemetry: default is to write data streams through `data_stream.dataset/namespace`. For a static index, set `logs_index`.
  - Filebeat: default is `filebeat-%{[agent.version]}-%{+yyyy.MM.dd}` managed by ILM. Before disabling ILM or using a custom static index, ask a separate confirmation question after Step 1 has been answered. The initial request does not count as confirmation to disable ILM or use a custom index, even when it explicitly asks to turn ILM off.
- OpenTelemetry only: mapping mode - confirm `otel` (default, recommended on ES 8.16+), `ecs`, `none`, `raw`, or `bodymap`. If the user is unsure, recommend `otel` for ES 8.12+; recommend `ecs` when the user wants flattened ECS-style fields. Wait for an explicit choice.

### Step 4 - Recommend Optional Features, But Do Not Add Them Automatically

Group the following options into **one** question and wait for the user to choose. Add only the options the user confirms.

OpenTelemetry:
- `memory_limiter` processor, recommended as the first processor in every pipeline to prevent collector OOM under backpressure; see `27-memorylimiterprocessor.md`.
- `batch` processor, recommended to reduce ES bulk overhead.
- `resourcedetection` for host/cloud metadata.
- `k8sattributes` to attach pod/namespace/node metadata when running in Kubernetes; see `29-k8sattributesprocessor.md`; requires RBAC.
- `attributes` / `resource` / `transform` for adding, deleting, or renaming attributes, OTTL transforms, and mapping mode overrides. Use `resource` for simple resource edits; use `transform` for OTTL.
- `filter` to drop noisy logs by severity, body match, or attribute value through OTTL; see `28-filterprocessor.md`.
- `redaction` to allow-list fields and mask/hash sensitive values; see `30-redactionprocessor.md`.
- `groupbyattrs` to promote labels such as `tenant_id` to Resource attributes for cleaner ES routing and batching; see `32-groupbyattrsprocessor.md`.
- `log_dedup` to merge repeated INFO/heartbeat logs into one record with a count; see `33-logdedupprocessor.md`.
- `routing` connector to distribute traffic to multiple ES clusters or indexes by tenant, severity, or service; see `34-routingconnector.md`.
- `file_storage` extension plus `storage:` on filelog for restart persistence.
- `sending_queue` / persistent queue on the exporter for reliability.

Filebeat:
- `add_host_metadata` + `add_cloud_metadata` processors.
- `decode_json_fields` when the log line is JSON-encoded.
- `setup.ilm` policy choice: default / custom / disabled.
- custom `setup.template`.
- `queue.disk` for persistence.

### Step 5 - Generate The Configuration

Choose the matching template under `assets/templates/` and replace placeholders with confirmed values. **Do not** introduce fields the user has not approved unless they are the minimum required for the file to load.

Generation rules:
- Generate YAML only after all required confirmation gates have explicit answers: technology stack, input source, Elasticsearch destination, and any sensitive behavior such as disabling ILM or using a custom index.
- Reference credentials through environment variables only.
- Use 2-space YAML indentation.
- Write only `service.pipelines.logs`; do not write `traces` or `metrics` pipelines unless the user asks for them.
- Verify that every component referenced under `service:` is declared at the top level.
- Explain unusual choices with one short comment line; do not add long explanations.

### Step 6 - Self-Check Before Returning

Mentally run this checklist. If any item fails, refuse to output the configuration:

- [ ] Single technology stack: OTel or Filebeat, never both.
- [ ] The Step 1 technology stack confirmation was answered in a separate user reply, or was already answered earlier in the conversation.
- [ ] Output points only to Elasticsearch.
- [ ] Input is log-shaped.
- [ ] Every component ID in `service.pipelines.logs` for OTel is declared at the top level, or `output.elasticsearch` is the only Filebeat output.
- [ ] Exactly one of `endpoint` / `endpoints` / `cloudid` is used in the OTel ES exporter.
- [ ] Exactly one authentication method is used: basic or api_key, never both.
- [ ] No inline secrets; all secrets are environment-variable references.
- [ ] No fields the user did not request, except the minimum fields required for loading.
- [ ] Filebeat `setup.ilm.enabled: false`, `output.elasticsearch.index`, or `indices:` appears only after a separate confirmation for ILM/custom index behavior.
- [ ] YAML is parseable: no tabs, consistent indentation, balanced lists.
- [ ] If `start_at: beginning` is **not** enabled, comment on the impact: existing file content will not be backfilled.

Then return:
1. The complete YAML, ready to save as `otelcol-config.yaml` or `filebeat.yml`.
2. A three-point "how to run / validate" footer:
   - OTel: `otelcol-contrib validate --config=otelcol-config.yaml`, then `otelcol-contrib --config=otelcol-config.yaml`.
   - Filebeat: `filebeat test config -c filebeat.yml`, `filebeat test output`, and `filebeat -e -c filebeat.yml`.

## Confirmation Policy

When unsure, **ask**. Use numbered question blocks; do not silently choose. Specifically:

- The initial user request never counts as the Step 1 technology stack confirmation. Only a later direct answer to the Step 1 question counts.
- Do not proceed past Step 1 in the same assistant response that asks for the technology stack.
- Do not pick an OTel ES exporter mapping mode when the ES version is unknown.
- Do not enable `start_at: beginning` without confirmation, because it changes which lines are sent.
- Do not disable ILM or set a custom index without a separate confirmation. The initial request does not count as confirmation to disable ILM or use a custom index, even when it explicitly asks to turn ILM off.
- Do not choose a TLS verification mode, `full` or `none`, without confirmation.

## Refusal Cases

Refuse these requests directly:
- Output to any destination other than Elasticsearch. Logstash-only is also refused; users may run Logstash separately, but this skill targets ES directly.
- Mix both technology stacks in one file.
- Generate multiple configurations in a single request.
- Use inputs unrelated to logs, such as raw metrics scraping or span generation.
- Use Syslog or Fluent forward as the log input source.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Inline a plaintext password in the file | Use `${env:ELASTIC_PASSWORD}` for OTel or `${ELASTIC_PASSWORD}` for Filebeat. |
| Default to `start_at: end` when the user wants backfill | Ask first; if the user wants existing content collected, set `beginning`. |
| Generate YAML immediately because the first prompt already says "Filebeat" | Ask the Step 1 technology stack question first, wait for a separate reply, and stop before generating YAML. |
| Add `traces` / `metrics` pipelines without being asked | Output only a `logs` pipeline unless the user requests otherwise. |
| Forget to declare a component referenced in `service.pipelines` | Always cross-check declared components against referenced components. |
| Blindly use `mapping.mode: ecs` | The default is `otel`; switch only when the user asks. |
| Set `setup.ilm.enabled: false` because the initial prompt asked for a custom index | Ask a separate ILM/custom-index confirmation after the stack is confirmed. |
| Use Filebeat ILM while also setting `index:` | Either confirm disabling ILM for the custom index or omit the custom index; choose one. |
| Use `verification_mode: none` without warning | Warn the user and prefer `full` with a CA file. |
