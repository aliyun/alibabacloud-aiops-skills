# OpenTelemetry resourcedetectionprocessor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/resourcedetectionprocessor/README.md

Detects resource attributes (host, cloud, container) and attaches them to telemetry.

## Top-level Configuration

```yaml
processors:
  resourcedetection:
    detectors: [ <string> ]      # see Valid Detectors below
    override: <bool>             # default true
    refresh_interval: <duration> # if unset, runs once at startup
    timeout: <duration>
```

## Valid Detectors

`env`, `system`, `docker`, `gcp`, `ec2`, `ecs`, `elastic_beanstalk`, `eks`, `lambda`, `azure`, `aks`, `heroku`, `openshift`, `dynatrace`, `consul`, `k8snode`, `kubeadm`, `hetzner`, `akamai`, `scaleway`, `vultr`, `oraclecloud`, `digitalocean`, `nova`, `upcloud`, `alibaba_ecs`, `tencent_cvm`, `ibmcloud_vpc`, `ibmcloud_classic`.

## System detector example

```yaml
processors:
  resourcedetection/system:
    detectors: [system]
    timeout: 2s
    override: false
    system:
      hostname_sources: [os]
      resource_attributes:
        host.name:
          enabled: true
        host.id:
          enabled: true
```

## hostname_sources

| Source | Behavior |
|--------|----------|
| `dns` | Lookup hosts file → CNAME → reverse DNS |
| `os` | Hostname from local kernel |
| `cname` | `net.LookupCNAME` |
| `lookup` | Reverse DNS of current host IP |

## Notes

- When multiple detectors emit the same attribute, first one wins.
- Recommended AWS ordering: `lambda → elastic_beanstalk → eks → ecs → ec2`.
- Most setups need only a single startup detection (no `refresh_interval`).
