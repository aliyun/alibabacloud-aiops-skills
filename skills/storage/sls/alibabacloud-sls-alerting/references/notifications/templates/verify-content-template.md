# Verify a content template

## Template verification

Validate the proposed template without requiring an existing action policy,
alert rule, or historical event. Read the stored template only for an update.

1. Run the [resource validator](../api/resource-records.md#local-validation-before-a-write)
   with `--input-kind value --purpose custom-write` on the complete proposed
   value. For a fetched object being inspected, use `--purpose read`.
2. Check expressions and control flow against [template syntax](syntax.md),
   and standard variable names and types against [template data](variables.md).
   Check custom result fields against the supplied query, schema, or sample.
   Identify unknown custom fields without requiring a live alert to resolve them.
3. Review missing optional values, empty result arrays, and firing/resolved
   branches. Check escaping for the selected channel, especially dynamic values
   embedded in JSON. These are static checks, not proof of service rendering.

Existing policies and event samples can supplement these checks when relevant
and available; their absence does not block template creation.

## Optional service rendering

No service template-preview API is verified by this skill. If a documented
preview interface is available in the target environment, inspect its rendered
subject/body and errors without sending a notification. A generic Jinja renderer
does not establish SLS rendering behavior.

For rendered JSON, save the body and run
`python3 -m json.tool rendered-body.json > /dev/null`. This checks JSON format.
Report static checks and service rendering separately; when no preview was run,
state that service rendering is unverified. An already authorized notification
can provide additional evidence, but is not an implicit fallback.
