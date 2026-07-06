# OpenTelemetry fluentforwardreceiver

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/receiver/fluentforwardreceiver/README.md

Listens on the Fluentd Forward protocol; useful as a drop-in for fluentd/fluent-bit forward output.

## Configuration

### `endpoint`

Listen address for the TCP server.
- TCP form: `host:port` (e.g., `0.0.0.0:8006`). UDP server on the same port handles heartbeat echoes.
- Unix domain socket: `unix://<path>`.

## Sample YAML

```yaml
receivers:
  fluentforward:
    endpoint: 0.0.0.0:8006

service:
  pipelines:
    logs:
      receivers: [fluentforward]
      exporters: [elasticsearch]
```

## Important Notes

- TLS is **not supported** by this receiver. For mTLS use a TLS-terminating sidecar or a different ingest path.
- The handshake portion of the Forward protocol (with `shared_key`) is also not supported.
- Supports all three event types: message, forward, and packed forward (incl. compressed).
