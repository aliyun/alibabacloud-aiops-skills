# Rich text

Use when adding Markdown or HTML content; only Markdown supports query-field substitution.

Start with the [HTML runbook note dashboard](../../assets/dashboards/charts/textpro.json)
for a complete example.

## Usage

- Markdown data placeholders read the first row; aggregate to one row. Use ${{field}} for a single query; ${{A.field}} for a field from query A in multiquery content.
- HTML content is static: query fields and dashboard variables are not substituted.
- Both modes sanitize content. Scripts and HTML event handlers cannot be used to add behavior.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `contentOption.mode` | string | Yes | — | markdown or html. |
| `contentOption.content` | string | Yes | None | Content in the selected format. |
| `markdownOption.markdownAlgin` | string[] | No | [] | Include horizontalCenter, verticalCenter, or both to center content. |

## Examples

Display fragments:

### Static markdown

```json
{
  "contentOption": {
    "mode": "markdown",
    "content": "### Guide\n\nDashboard guidance and troubleshooting steps."
  }
}
```

### Dynamic markdown summary

```json
{
  "contentOption": {
    "mode": "markdown",
    "content": "### Summary\n\nRequests: ${{total}}\n\nErrors: ${{errors}}"
  }
}
```

### Centered static html

```json
{
  "contentOption": {
    "mode": "html",
    "content": "<div><h3>Usage notes</h3><strong>Service status summary</strong></div>"
  },
  "markdownOption": {
    "markdownAlgin": [
      "horizontalCenter",
      "verticalCenter"
    ]
  }
}
```
