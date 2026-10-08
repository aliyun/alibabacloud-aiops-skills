# Markdown panel

Use when adding Markdown notes or query-driven text to a dashboard.

Start with the [static Markdown note dashboard](../../assets/dashboards/charts/markdownpro.json)
for a complete example.

## Usage

- Static content needs no query.
- Data placeholders use the first row, so aggregate to one row. Use ${{field}} for a single query and ${{A.field}} to identify fields from multiple queries.
- `${field}` is also supported for query-field substitution. Use either `${field}` or `${{field}}` consistently within one body; do not mix the two forms.
- Content supports dashboard variables.
- Markdown content is sanitized; scripts cannot be used to add behavior.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `markdownStr` | string | Yes | None | Markdown content. |
| `markdownOption.markdownAlgin` | string[] | No | [] | Include horizontalCenter, verticalCenter, or both to center content. |

## Examples

Display fragments:

### Static markdown

```json
{
  "markdownStr": "### Guide\n\n- Check error trends\n- Inspect error details"
}
```

### Single row summary

```json
{
  "markdownStr": "Current requests: ${{total}}"
}
```
