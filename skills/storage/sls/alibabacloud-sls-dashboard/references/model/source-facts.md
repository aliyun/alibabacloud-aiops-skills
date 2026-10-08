# Source facts

The [schema](../contracts/source-facts.schema.json) defines source, fields,
metrics, evidence and warnings, with optional metadata/sample and view members.
Source id/type/region/project/name must match the Plan.

Field indexed/analytics values are booleans or null for unknown. Samples
do not establish indexing or analytics support. Preserve proven index types;
use unknown when the sample alone does not establish a type.

Keep metric names, their labels, the observation window and sample provenance
together. sampleCardinality counts distinct sampled values, not all possible values.
StoreView members keep individual field capabilities and memberErrors; top-level
fields do not prove uniform member support.

discover --output writes complete evidence alongside the facts in a .evidence
directory. Evidence includes operation, source kind, hash, raw path, execution progress,
limits and member failures.

Explicit user input and existing JSON are valid evidence. The builder checks supplied
facts' structure/identity; full SQL expression semantics still require index evidence
and query verification.
