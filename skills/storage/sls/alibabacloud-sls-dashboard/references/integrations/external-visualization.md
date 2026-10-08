# External visualization

Choose the Grafana connection before writing queries:

| Connection | Query language and use |
| --- | --- |
| Native SLS plugin | Logstore uses SLS indexed search and SQL; Metricstore supports SQL and PromQL. Supports Grafana template variables. |
| Elasticsearch-compatible interface | Uses Elasticsearch-compatible requests and Lucene filters in Grafana, not SLS SQL. Requires indexes on the queried logs. |
| Metricstore Prometheus-compatible protocol | Uses PromQL for metric series. |

Use DataV for visual composition and large-screen layouts, or Tableau for BI and
reporting. Check region, source access, authentication, refresh interval, query
cost and destination limits before connecting. Configure credentials in the
external system's datasource settings; do not place them in Dashboard JSON.

Keep each system's JSON format and variable syntax separate. Managing an external
Grafana deployment is outside this skill.

- [Grafana SLS plugin](https://help.aliyun.com/zh/sls/developer-reference/connect-log-service-to-grafana)
- [Elasticsearch compatibility](https://help.aliyun.com/zh/sls/use-grafana-to-access-the-elasticsearch-compatible-api-of-log-service)
- [Metricstore/Grafana](https://help.aliyun.com/zh/sls/send-time-series-data-from-log-service-to-grafana)
- [DataV](https://help.aliyun.com/zh/sls/developer-reference/connect-log-service-with-datav)
