# Copy, import, and export

Export complete Dashboard JSON with `dashboard-get`. For a copy, specify the
target account/profile, region, project and dashboard name independently of query
sources. Remap only requested datasources; validate fields, queries, tokens and
layout in the target environment.

Inspect changes and publish through the regular workflow. A copied dashboard does
not copy data, indexes or permissions. Preserve the source baseline. Grafana-to-SLS
dashboard JSON conversion is not supported.

[Official import/export guidance](https://help.aliyun.com/zh/sls/import-and-export-sls-dashboards)
