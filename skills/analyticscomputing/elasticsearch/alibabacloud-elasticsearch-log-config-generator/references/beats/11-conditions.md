# Filebeat — processor conditions

> Source: https://www.elastic.co/guide/en/beats/filebeat/current/defining-processors.html
>
> Referenced by every processor entry in `06-processors.md`. The `when:` / `if:` block accepts the conditions below.

## General processor form

```yaml
processors:
  - <processor_name>:
      when:
        <condition>
      <parameters>
```

For multiple processors gated by one condition:

```yaml
processors:
  - if:
      <condition>
    then:
      - <processor_a>:
          ...
    else:
      - <processor_b>:
          ...
```

Processors may be top-level (apply to everything) or under a specific input (apply only to that input).

## Conditions

### `equals`

```yaml
equals:
  http.response.code: 200
```

### `contains`

```yaml
contains:
  status: "Specific error"
```

### `regexp`

```yaml
regexp:
  system.process.name: "^foo.*"
```

### `range`

`lt`, `lte`, `gt`, `gte`. Supports shorthand and multi-bound forms.

```yaml
range:
  http.response.code:
    gte: 400

range:
  http.response.code.gte: 400

range:
  system.cpu.user.pct.gte: 0.5
  system.cpu.user.pct.lt: 0.8
```

### `network`

CIDR or named range (`loopback`, `unicast`, `multicast`, `private`, `public`, `unspecified`, `link_local_unicast`, …). IPv4 + IPv6.

```yaml
network:
  source.ip: private

network:
  destination.ip: '192.168.1.0/24'

network:
  destination.ip: ['192.168.1.0/24', '10.0.0.0/8', loopback]
```

### `has_fields`

```yaml
has_fields: ['http.response.code']
```

### `or` / `and` / `not`

```yaml
or:
  - equals:
      http.response.code: 304
  - equals:
      http.response.code: 404

and:
  - equals:
      http.response.code: 200
  - equals:
      status: OK

not:
  equals:
    status: OK
```

Combining `<c1> OR (<c2> AND <c3>)`:

```yaml
or:
  - <condition1>
  - and:
    - <condition2>
    - <condition3>
```

## Examples

### Drop events on a status code

```yaml
processors:
  - drop_event:
      when:
        equals:
          http.response.code: 200
```

### Drop fields on HTTP errors only

```yaml
processors:
  - drop_fields:
      when:
        range:
          http.response.code:
            gte: 400
      fields: ["debug_payload"]
```

### Tag external traffic

```yaml
processors:
  - add_tags:
      when:
        not:
          network:
            source.ip: private
      tags: [external]
```

### if/then/else with combined condition

```yaml
processors:
  - if:
      and:
        - equals:
            http.response.code: 200
        - has_fields: ['user.id']
    then:
      - add_fields:
          target: audit
          fields:
            ok: true
    else:
      - drop_event: {}
```

### Per-input processor (filestream)

```yaml
- type: filestream
  processors:
    - drop_event:
        when:
          contains:
            message: "healthcheck"
```
