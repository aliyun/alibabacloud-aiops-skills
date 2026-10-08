# Interaction events and drilldowns

Use when a chart click should open a dashboard, log query, Trace view, or custom
URL with values from the selected data point.

Use placeholders such as `${{host}}` for a clicked field, `${{__field.name}}`,
`${{__value.raw}}`, `${{token:service}}` for a dashboard token, and
`${{__start_time__}}`, `${{__end_time__}}`, `${{__interval__}}` for source-query time.
Navigation sets the target page's initial filters and variables without changing its
saved queries. Source-time placeholders in `searchFilter` retain the source interval.

A selected source interval takes precedence over `timeRange`. Otherwise, `-3`
uses the clicked time field. For an absolute source interval, any other nonzero
`timeRange` inherits that interval, including presets and `-2`. With a relative
source interval, the configured target preset or inheritance mode applies.

## Configuration parameters

Each `display.actionOptions[]` entry contains a matcher and an event list.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `matcher.id` | string | Yes | None | byName for a field, byFrameRefID for a query, byRegexp for matching field names. |
| `matcher.refId` | string | No | None | Limit byName or byRegexp matching to this query. |
| `matcher.options` | string or string[] | Except byFrameRefID with refId | None | Field name for byName; query name for byFrameRefID; pattern for byRegexp. |
| `events` | object[] | Yes | [] | Actions offered when the matching field is clicked. |
| `events[].event` | string | Yes | None | dashboard, logstore, logstoreview, savedSearch, trace, traceDetails, or link. |
| `events[].values.name` | string | Yes | None | Action label. |
| `events[].values.blank` | boolean | No | — | Open a new tab; HTTP(S) links outside the current origin open a new tab even when false. |
| `events[].values.timeRange` | number | No | — | Subject to the source-time precedence above: -2 keeps target defaults; -1 inherits source time; -3 uses a clicked time field. Presets include 2 for the last 15 minutes, 3 for the last hour, and 5 for the last 24 hours. |
| `events[].values.timeRangeField` | string | For timeRange=-3 | None | Clicked-row time field. |
| `events[].values.timeRangeFieldDiff` | number | No | 300 | Seconds before and after the selected time. |
| `events[].values.filterInherit` | boolean | No | — | Carry source filters to dashboard, logstore, logstoreview, or savedSearch targets. |
| `events[].values.tokenInherit` | boolean | No | — | Carry source tokens to a dashboard target, excluding keys configured in searchToken or searchStaticToken. |
| `events[].values.searchFilter` | string | No | None | Additional target filter with clicked-value or token placeholders; not used by traceDetails. |
| `events[].values.searchToken` | object[] | No | [] | For dashboard and savedSearch: {key,value} maps target token keys to clicked-context variable names. An empty value or __sls__trigger_col__ uses the clicked value; an unavailable named variable produces no assignment. |
| `events[].values.searchStaticToken` | object[] | No | [] | {key,value} entries setting constants; override dynamic values for the same keys. |

An explicit token key excludes the inherited key even when its selected source
variable has no value. Use variables present in the clicked context.

In target URLs, `queryTimeType=99` denotes an absolute interval with Unix-second
`startTime` and `endTime`. These are URL parameters; setting `timeRange=99` in an
action does not define an absolute interval.

### Destination parameters

Paths below are relative to each event's `values`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `project` | string | For dashboard, logstore, logstoreview, savedSearch | None | Target project. |
| `dashboardName` | string | For dashboard | None | Target dashboard; __TARGET_SELF__ refers to the current dashboard. |
| `logstoreName` | string | For logstore | None | Target Logstore. |
| `logstoreviewName` | string | For logstoreview | None | Target log StoreView. |
| `savedSearchName` | string | For savedSearch | None | Target saved query. |
| `trace.project` | string | For trace and traceDetails | None | Project containing the target Trace instance. |
| `trace.instanceId` | string | For trace and traceDetails | None | Target Trace instance ID. |
| `traceID` | string | For traceDetails | None | Clicked-context variable name containing the Trace ID, without placeholder syntax; not a literal Trace ID. |
| `spanID` | string | For traceDetails | None | Clicked-context variable name containing the span ID, without placeholder syntax; not a literal span ID. |
| `protocol` | string | For link | None | http, https, or custom. |
| `customProtocol` | string | For custom protocol | None | Protocol prefix. |
| `link` | string | For link | None | Destination address after the protocol; supports clicked-context variables. |

`trace` opens Trace analysis and applies `searchFilter`. `traceDetails` opens the
Trace and span selected by `traceID` and `spanID`, without applying `searchFilter`.
Both use the time-range and `blank` settings, but not filter or token inheritance.

### Documentation links

For explanatory links in the chart header, use `display.documentLinkOption`:

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `documentLinks` | object[] | Yes | [] | Entries containing title and url. |
| `documentLinks[].title` | string | Yes | None | Link label. |
| `documentLinks[].url` | string | Yes | None | URL including its protocol. |
| `showIcon` | boolean | No | false | Show a link icon when there is exactly one link. |

## Configuration examples

Configure a field matcher, then place the chosen event objects in its `events` list:

```json
{
  "display": {
    "actionOptions": [
      {
        "matcher": {
          "id": "byName",
          "refId": "A",
          "options": "status"
        },
        "events": []
      }
    ]
  }
}
```

```json
{
  "event": "dashboard",
  "values": {
    "name": "View host details",
    "project": "demo-project",
    "dashboardName": "host-detail",
    "blank": false,
    "timeRange": -1,
    "filterInherit": true,
    "tokenInherit": true,
    "searchFilter": "host: ${{host}} and service: ${{token:service}}",
    "searchToken": [
      { "key": "status", "value": "__sls__trigger_col__" },
      { "key": "host", "value": "host" }
    ],
    "searchStaticToken": [
      { "key": "env", "value": "prod" }
    ]
  }
}
```

```json
{
  "event": "logstore",
  "values": {
    "name": "View related logs",
    "project": "demo-project",
    "logstoreName": "nginx-log",
    "blank": true,
    "timeRange": -1,
    "filterInherit": true,
    "searchFilter": "host: ${{host}} and status: ${{status}}"
  }
}
```

```json
{
  "event": "logstoreview",
  "values": {
    "name": "View log StoreView",
    "project": "demo-project",
    "logstoreviewName": "nginx-view",
    "timeRange": -1,
    "filterInherit": true,
    "searchFilter": "host: ${{host}}"
  }
}
```

```json
{
  "event": "savedSearch",
  "values": {
    "name": "Open error query",
    "project": "demo-project",
    "savedSearchName": "error-search",
    "timeRange": -1,
    "filterInherit": true,
    "searchFilter": "status: ${{status}}",
    "searchToken": [
      { "key": "host", "value": "host" }
    ],
    "searchStaticToken": []
  }
}
```

### Trace analysis and details

For a clicked row containing `service`, `trace_id` and `span_id`, use these event
entries with the target Trace Project and instance:

```json
[
  {
    "event": "trace",
    "values": {
      "name": "Analyze traces",
      "trace": {"project": "demo-project", "instanceId": "demo-trace"},
      "timeRange": -1,
      "searchFilter": "service: ${{service}}"
    }
  },
  {
    "event": "traceDetails",
    "values": {
      "name": "Open trace details",
      "trace": {"project": "demo-project", "instanceId": "demo-trace"},
      "traceID": "trace_id",
      "spanID": "span_id",
      "timeRange": -1
    }
  }
]
```

### Custom link

```json
{
  "event": "link",
  "values": {
    "name": "Open ticket system",
    "protocol": "https",
    "link": "ticket.example.com/search?host=${{host}}",
    "blank": true
  }
}
```
