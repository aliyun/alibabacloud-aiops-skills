# Edit dashboard content

Dashboard JSON identifies charts by `title`. Visible titles, queries and display
settings are separate fields, so a title or style edit can be made directly in the
corresponding chart object.

An existing Dashboard JSON document can serve as the working input;
[dashboard reads](publish.md#existing-configuration) can supply it when needed.

[Row sections](../charts/dashboardrow.md), [variables](../features/variables.md) and
[actions](../features/actions.md) describe dependencies relevant to removing charts
or changing IDs and query fields. [Layout](../features/layout.md) describes panel positions.

## Add or combine charts

Chart objects from [examples](../charts/examples.md) or another configuration can
be added to `charts[]`.
`merge-additions` appends their chart objects and checks for ID collisions:

```sh
python3 scripts/dashboard/dashboard.py merge-additions --base working.json \
  --additions additions.json --output final.json
```

For update validation against an original get response, the command also accepts
`--mode update --baseline source.json`. `--report merge-check.json` saves its report.

## Compare and check

The tools can summarize changes and classify existing versus introduced problems:

```sh
python3 scripts/dashboard/dashboard.py diff --before source.json --after final.json
python3 scripts/dashboard/dashboard.py validate --mode update --input final.json --baseline source.json
```

The [validation guide](../validation/checks.md) explains the results.
[Publishing](publish.md) provides CLI commands for saving the configuration.
[Copy/import](../integrations/copy-and-import.md) covers a different destination.
