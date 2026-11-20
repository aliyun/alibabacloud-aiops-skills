# Phrase Search

## When to use

Prefer ordinary index search when keyword presence is enough. Consider phrase search when
the words must also be adjacent and in order, such as a known error-message fragment or a
sequence within a path that ordinary matching cannot distinguish.

For character-level substring matching, exclusion, or filtering followed by SQL analysis, consider SQL `LIKE`
or regular expressions with the required analysis indexes. Keep usable index filters before
the pipe to reduce the input.

## Syntax and matching

Use `#"..."` with the full-text index, or `field:#"..."` to search a specific indexed field:

```text
#"Alpha Beta"
body:#"Alpha Beta"
```

Ordinary `body:"Alpha Beta"` can match `Alpha Extra Beta` or `Beta Alpha`. Phrase search
requires the indexed terms to be adjacent and in order. It is not whole-field equality or
a character-by-character substring match.

When spaces, hyphens, and commas are token delimiters, `body:#"Alpha-Beta"`,
`body:#"Alpha Beta"`, and `body:#"Alpha,Beta"` match the same token sequence.
See [index matching rules](../index/index-configuration.md#text-matching) for tokenization and case sensitivity.

## Restrictions

- Double quotes are required around the phrase.
- Phrase search cannot be combined with wildcards, `not`, or an SQL analysis statement.

## Counts

The log histogram counts the corresponding ordinary search, not the final phrase matches.
Do not use that count as the total number of phrase matches.

Source: [Official phrase-search reference](https://help.aliyun.com/zh/sls/phrase-search).
