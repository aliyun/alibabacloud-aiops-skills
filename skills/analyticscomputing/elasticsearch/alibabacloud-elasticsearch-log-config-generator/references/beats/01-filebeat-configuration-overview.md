# Filebeat Configuration Overview

> Source: https://www.elastic.co/docs/reference/beats/filebeat/configuring-howto-filebeat

To set up Filebeat, modify its configuration file (default `filebeat.yml`). A companion `filebeat.reference.yml` ships every non-deprecated option as a comprehensive example.

## Top-level configuration sections

A typical `filebeat.yml` contains:

- `filebeat.inputs:` — list of inputs (filestream, log, kafka, http_endpoint, etc.).
- `filebeat.modules:` — Beats modules (nginx, system, mysql, ...).
- `processors:` — processor pipeline applied before output.
- `output.elasticsearch:` (or `output.logstash`, etc.) — destination.
- `queue:` — internal queue (memory or disk-spool).
- `setup.template:` and `setup.ilm:` — index template and ILM management.
- `setup.kibana:` — Kibana endpoint for dashboards/policies.
- `logging:` — Filebeat's own logging.
- `http:` — HTTP endpoint for status info.
- `monitoring:` — stack monitoring shipping.

## Sub-Topics referenced from the overview

- Inputs — `configuration-filebeat-options`
- Modules — `configuration-filebeat-modules`
- General settings — `configuration-general-options`
- Project paths — `configuration-path`
- Config file loading — `filebeat-configuration-reloading`
- Output — `configuring-output`
- SSL — `configuration-ssl`
- Index lifecycle management (ILM) — `ilm`
- Elasticsearch index template — `configuration-template`
- Kibana endpoint — `setup-kibana-endpoint`
- Kibana dashboards — `configuration-dashboards`
- Processors — `filtering-enhancing-data`
- Autodiscover — `configuration-autodiscover`
- Internal queue — `configuring-internal-queue`
- Logging — `configuration-logging`
- HTTP endpoint — `http-endpoint`
- Regular expression support — `regexp-support`
- filebeat.reference.yml — `filebeat-reference-yml`

## Validation & startup

```bash
filebeat test config -c /etc/filebeat/filebeat.yml
filebeat test output    # verifies it can connect to ES
filebeat -e -c /etc/filebeat/filebeat.yml   # run in foreground
```
