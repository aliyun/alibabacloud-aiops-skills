# Common analysis patterns

| Goal | Suggested panels |
| --- | --- |
| Gateway/access logs | Traffic, errors, latency; host/path/method breakdown; records |
| Application logs | Error trend, service/exception ranking, samples and trace identifiers |
| Audit logs | Actors, actions, targets, failures and originating locations |
| Infrastructure metrics | Health, resource trends, saturation/rankings, object labels |
| Application metrics | Traffic, error ratio, latency, resource saturation |
| Unknown logs | Log volume trend, indexed-field breakdowns, sample records |

Choose sections supported by the available fields. Error ratios need an explicit
denominator; latency percentiles need a valid measure/distribution. Treat request IDs
and other high-cardinality fields as detail dimensions rather than default series
splits. Place parent selectors before dependent selectors.
