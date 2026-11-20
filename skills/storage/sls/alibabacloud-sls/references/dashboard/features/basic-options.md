# Basic display options

Use when changing a panel title, description, links, or its independent time window.
Parameters belong to `display.basicOptions`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `displayName` | string | Yes | None | Visible panel title; does not change the chart identifier. Set it explicitly; omitting it can leave the panel header blank. |
| `description` | string | No | None | Help text beside the title; supports line breaks. |
| `links` | object[] | No | [] | Header links. Each entry uses title, url, and targetBlank; multiple links form a menu. |
| `links[].title` | string | Yes, for a link | None | Link label. |
| `links[].url` | string | Yes, for a link | None | Destination URL. |
| `links[].targetBlank` | boolean | No | — | Whether to open a new tab. |
| `showTitle` | boolean | No | — | Show the header, including title, description, time, links, and header actions. |
| `showBorder` | boolean | No | — | Show the panel border. |
| `showBackground` | boolean | No | — | Show the panel background. |
| `showTime` | boolean | No | true | Show the query time in the header; does not change the query window. |
| `fixedTime` | boolean | No | false | Use search.start/end/timeSpanType instead of dashboard time. |

A relative fixed window still advances with the current time; an absolute window
stays at its saved timestamps. See [time settings](../queries/time-and-limits.md) for window selection.

## Documentation links

`basicOptions.links` supports a new-tab choice per link. `documentLinkOption`
provides a single-link icon option; [image panels](../charts/imagepro.md) use this format.

For explanatory links in the chart header, use `display.documentLinkOption`:

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `documentLinks` | object[] | Yes | [] | Entries containing title and url. |
| `documentLinks[].title` | string | Yes | None | Link label. |
| `documentLinks[].url` | string | Yes | None | URL including its protocol. |
| `showIcon` | boolean | No | false | Show a link icon when there is exactly one link. |
