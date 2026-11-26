# Validate answers using evidence already read

Use the source-extract workflow below for summaries, Wiki/content, and Graph knowledge. Use the existing TSV AnswerContract workflow in the later sections for structured fields, sets, and exact calculations. Both run locally with POSIX Python 3.10+ and the standard library; their safe-file flags and private-directory operations are not a claim of Windows support. Neither calls an API, reads environment/default configuration or credentials, downloads Sources, reads benchmark/reference answers, or starts an Agent. Local validation cannot prove intent, relevance, business truth, complete coverage, or live identity; semantic review remains necessary.

## Source extracts from unstructured knowledge

When this Skill is installed, use `scripts/knowledge_answer.py` for supplied-evidence knowledge answers. Read the installed entry point first, then create and fill the private job yourself. Run from the Skill root, or use the absolute installed helper path from another working directory. The parent directory passed to new-job must exist and be trusted and approved for outputs by the host. If that explicitly specified output parent is absent, create it locally first; a local path error does not require cloud runtime setup. Do not default to a shared temporary location when the host restricts writes to its output directory. The helper creates a unique directory with mode 0700 and exclusive job file with mode 0600. Carry the exact returned path between tool calls; do not derive it from evidence text.

```bash
CONTEXT_GRAPH_OUTPUT_DIR='<existing host-approved outputs directory>'
CONTEXT_GRAPH_EXTRACT_JOB="$(python3 -S scripts/knowledge_answer.py new-job --directory "$CONTEXT_GRAPH_OUTPUT_DIR")"
```

If you already have the complete JSON job, use `new-job --directory "$CONTEXT_GRAPH_OUTPUT_DIR" --from-stdin` and supply that JSON on standard input. A quoted here-document preserves the JSON as data. The helper checks the input budget and job envelope, creates the private file, and prints its exact path. Use `render` to validate the original batch, selections, and source bindings before answering.

To fill an empty job, write a JSON object into that owned file. If the host editor requires a prior read, read the generated job file before writing it. If a write fails for that reason, read the same private job and retry the write. Use `schema: context-graph-knowledge-answer-job-v1`, the original `question`, the full unmodified successful `responses`, and `selections`. Each selection has a zero-based `response_index`, an RFC 6901 `pointer` within that response, and optionally a `quote` that is an exact contiguous substring of the selected string. Omit quote to preserve the whole original string or actual JSON value. No conclusion, reason, citation label, or other free business prose field is accepted. A neutral synthetic example is:

```json
{
  "schema": "context-graph-knowledge-answer-job-v1",
  "question": "Which items does the rule cover?",
  "responses": [{
    "Action": "GetKnowledgePoint", "Success": true, "RequestId": "synthetic-request",
    "Data": {
      "KnowledgeBaseId": "synthetic-kb", "Type": "WIKI", "Id": "synthetic-point", "Warnings": [],
      "Wiki": {"Title": "Synthetic rule", "Content": "The rule covers reviewed items."}
    }
  }],
  "selections": [{"response_index": 0, "pointer": "/Data/Wiki/Content"}]
}
```

Allowed sources are actual `RetrieveKnowledgePoints` result `Summary` strings, `GetKnowledgePoint` Wiki/KnowledgeContent `Title` or `Content`, and Graph subtrees. Graph selections preserve actual JSON and source bindings; no join, cardinality, independence, comparison, or enum meaning is derived. Source URL, credential, and arbitrary envelope fields cannot be selected. Full source identity, title, filename and RequestId are computed from the bound source; JSON audit also retains actual pointer and content/excerpt hashes. No source identity or label is supplied separately by the Agent. Finite floating score metadata is accepted in original responses.

Optional `unconfirmed_question_fragments` is a list of nonempty literal substrings of the original question, not free-form absence claims. Optional `applicability_unresolved: true` is allowed only when selections bind at least two distinct actual source identities. Use it to leave alternative applicability unresolved without choosing a source. With no extracts, list at least one unconfirmed question fragment; an empty selection does not prove global absence. An empty unknown list says only that none were listed, not that every condition or exception is known. All original response warnings remain visible, including warnings from responses not selected for excerpts.

```bash
python3 -S scripts/knowledge_answer.py render --input "$CONTEXT_GRAPH_EXTRACT_JOB" --language en --format json
python3 -S scripts/knowledge_answer.py render --input "$CONTEXT_GRAPH_EXTRACT_JOB" --language en --format markdown
```

Use `--language zh` for Chinese display labels; original evidence remains unchanged in either language. Markdown has conclusion, evidence, and unconfirmed-item sections, with untrusted text and metadata fenced as literal data using delimiters safe against embedded fences. JSON always has `semantic_review_required: true`; `validated_extracts` is no semantic acceptance claim. Check requested coverage and source relevance independently. Repair at most twice using only the same original batch, without extra API calls, installation, or human input. Complete artifact/log writes first and deliver exactly the rendered Markdown as the final answer, with no appended business prose or completion receipt.

When the user or trusted host supplies an authoritative fingerprint of the original response list, add `--expected-response-sha256 <supplied-lowercase-sha256>` to render. The optional argument must contain exactly 64 lowercase hexadecimal characters. Canonical input for this hash is UTF-8 JSON of `responses`, with sorted object keys, ensure_ascii=False, allow_nan=False, and compact comma/colon separators. Object key order and whitespace do not matter; array order, identities, content, and finite floating values do. The renderer checks the bounded original input before processing selections and returns fixed `BatchDigestMismatch` with exit 2 when the copied responses differ. Copy the authoritative fingerprint unchanged; recomputing it from a draft job would defeat this guard. Repair only the local copy from the same original batch, at most twice; then end without human follow-up. Without a supplied fingerprint, existing calls retain their original behavior. Neither mode verifies live identity, response authenticity, relevance or semantic correctness; no new job field or free prose is accepted.

Add optional `--full-selected-fields` when the complete text of each selected field must be preserved. A supplied quote remains a required exact contiguous anchor, but the renderer outputs the entire original selected value, retaining adjacent scope, conditions, exceptions, and recorded unknowns. Without this flag, a quote still narrows the excerpt as before. Actual Graph subtrees and raw values remain unchanged. For a selection inside Graph Edges, the citation also identifies the selected edge endpoints from the same detail. A single edge keeps its original FromNodeId and ToNodeId; a uniquely identified node with a returned name contributes NodeId and Name. A missing name stays unknown. Selecting the complete Nodes list also cites the edge IDs, direction and relationship types actually returned among those nodes. Selecting an individual node property keeps its narrow scope. For a join question, select the complete JoinKeys and use the edge direction when interpreting its pairs. Choose the actual readable fields needed for the question. Existing byte/output budgets and semantic-review requirements apply equally to whole-field rendering; oversized fields fail rather than being silently shortened.

Valid source-extract jobs exit 0 including disclosed unknowns; invalid input exits 2 with fixed safe error codes and no raw exception or input echo. Input is a bounded regular JSON file opened with O_NOFOLLOW and O_NONBLOCK, never modified. Limits are 8 MiB input, depth 32, 300000 structure nodes, 64 responses, 128 selections, and 16 MiB output. Duplicate keys, nonfinite numbers, invented quotations, invalid identities/branches/pointers, unknown schema fields, unsafe files, and excessive resources are rejected. The helper has no network, SDK, subprocess, or credential dependencies. It validates caller-supplied response structure, not response authenticity or current authorization.

## Structured TSV workflow

The remaining workflow processes only successful GetKnowledgePoint details already read in the current batch. It ensures that bound fields, sets, and exact calculation results are all addressed in the rendering. It cannot recognize question intent or prove the business meaning of labels, bindings, or relationships.

Define `required_slots` from the question before retrieval. After reading content, bind actual TSV column names. Define requested IDs, names, and dates separately without imposing a universal field set. The tool accepts evidence-supported schemas across business domains; examples below do not define a required business model. When TSV is absent, use source extracts instead of fabricating a table or complete-scope declaration.

## Job structure

Use `schema: context-graph-answer-job-v1`. Top-level fields are only `schema/context/tables/operations/contract/bindings/draft`; operations is optional. No free-prose field or precomputed pass report is accepted.

- `context`: required `batch_id`, nonsecret string `identity_scope`, `region`, and `snapshot` (null if unknown); optional `endpoint` and `KnowledgeBaseIds`. Endpoint uses the existing HTTPS host validation. Omitted base scope represents prior permission-based discovery, not tool-verified live identity. Include no Token, Cookie, AccessKey, or other secrets.
- `tables`: 1-32 entries with only `name/response/primary_key` and optional `block/coverage`. Response is the full successful GetKnowledgePoint output for WIKI or KNOWLEDGE_CONTENT, with RequestId, full KB/Type/Id, and Warnings. Existing request/response validation checks identities and rejects responses outside explicit base scope.
- Cache full successful detail JSON unchanged, including Action, RequestId, Data's KnowledgeBaseId/Type/Id, Content, and Warnings, not only Label/Content. Reuse only within the original identity, endpoint, region, base scope, and version. If a historical export kept only a projection, recover request identity only from that same call's request record and label it "projection reconstruction"; do not call it a complete original wire response or live identity verification. Never fabricate a merged successful API response.
- `primary_key`: explicitly list one or composite columns; do not guess header aliases, foreign keys, or business relationships. Reject empty keys. Deduplicate equal full rows with equal keys while retaining every source row; reject conflicting rows under one key. Also reject different content hashes for the same KB/Type/Id within a job.
- Read the sole TSV fenced block or plain TSV by default. Multiple TSV blocks require a zero-based `block` index. Fences are scanned linearly; reject nesting/unclosed fences and more than 128 TSV blocks. Other content is not a table. Standard CSV quoting supports tabs/newlines inside quoted cells. Reject duplicate/empty headers and inconsistent widths. Preserve empty strings rather than inventing 0/False.
- `coverage`: only `dataset/snapshot/row_count/basis`. Basis must occur verbatim in content; snapshot must match nonnull context.snapshot; row_count must equal deduplicated primary-key count. A header-only table with row_count=0 can declare a known empty table. Completeness is **caller-declared/source-quoted**, not proof of complete business reality. Top-N, final catalog pages, and page counts cannot create it. CONTENT_TRUNCATED/RESULT_TRUNCATED always prevent completeness.
- `contract`: only `question_id/question_type/required_slots`. Types are basic/association/multihop/aggregate/boundary. Each slot has `name/label/cardinality/format`, plus optional `completeness`. Cardinality is one/set; format is text/id/date/number; completeness is complete/observed. Sets default to complete, single values to observed. Use format=date only for evidence-supported full YYYY-MM-DD calendar dates. Use text for timestamps, periods, or other source formats; preserve their precision and never invent a missing date component. A status label cannot replace a requested date.
- `bindings`: exactly the slot names. A field binding is `{"table":"logical-table-or-operation-id","column":"actual-column","where":{"actual-column":"exact-value"}}`; omit `where` or use `{}` to select all observed rows. A calculation binding is `{"calculation":"operation-id"}`. Where accepts only string equality, not SQL, expressions, or fuzzy matching.
- `draft`: slot names mapped to string arrays. Numbers are strings too: use exact decimals, not bool, JSON floating values, substring matches, or rounding. Repeating ratios may use exact fractions such as `1/3`, compared through Decimal/Fraction; `0.333` is not `1/3`.

A one slot matching multiple primary-key subjects is ambiguous even if field values match. A set recomputes expected values from evidence and checks missing/extra in both directions. Equal values may be deduplicated while retaining all sources. An unmatched set in a complete scope may be empty; a partial empty set cannot establish global absence. A missing one subject is always unknown. Missing columns, empty values, absent subjects, and ambiguities remain explicit gaps, not resolved facts. Unknown snapshots/partial evidence cannot satisfy complete slots. A one/default-observed or explicitly observed value can resolve within this batch, but the resulting observed status proves neither a current state nor global completeness.

## Bounded operations

Operations execute in order, at most 50. IDs cannot collide with table/operation names; table references must already exist.

```json
[
  {"id":"combined","type":"union","tables":["fragment_a","fragment_b"]},
  {"id":"published","type":"select","table":"objects","where":{"state":"Published"}},
  {"id":"related","type":"join","left":"objects","right":"definitions","on":[{"left":"definition_id","right":"id"}]},
  {"id":"members","type":"group","table":"objects","by":["domain"],"member_columns":["id","name"]},
  {"id":"total","type":"count","table":"objects"},
  {"id":"ratio","type":"ratio","numerator":"published","denominator":"objects"}
]
```
This array illustrates operation formats, not a runnable job; define the input tables before using these operations.

`union` merges only 2-32 explicitly listed distinct already-read tables with identical column order, primary keys, and snapshots. Equal keys/full rows are deduplicated with every original cell source retained; conflicting rows/schema/keys are rejected. Inputs remain unchanged. Preserve original point identity, RequestId, hash, and row/column anchors; identical anchors may deduplicate, distinct sources must remain. Union is **always partial**, even when fragments declare completeness. Pagination end, consecutive IDs, or fragment counts do not prove a complete logical table. Unknown snapshots permit union of historical batch fragments and observed slots, without relaxing join restrictions.

`join` and its `map_description` alias use explicit composite-key equality in on, returning `left.original-column/right.original-column` with both primary keys/sources. Choose keys only from actual schemas and evidence-supported relationships. Description-based equality is optional and does not establish identity or a business relationship by itself; use it only when the evidence supports that mapping. Retain all matching candidates rather than selecting the first. These operations cannot validate the business meaning of a key or mapping; review it semantically. Reject empty join keys and unknown/different snapshots.

`group` retains every original member primary key, specified fields, and count; reject empty group/member fields. `count` uses original-primary-key deduplication. A ratio numerator must be a subset of its denominator with the same data domain and primary-key semantics. Domain hashes use full identity, content hash, selected TSV block/character range, primary key, declared dataset, and snapshot; different blocks/datasets cannot mix. Select inherits domain unchanged, independent of aliases/filters. Join derives domain from parents, explicit on, and type. Union derives it from sorted unique parent domains, column order, key, and snapshot, independent of parent aliases/input order. Prefer selects of one base table for ratios. Selects from one union may compute observed ratios with require_complete:false, remaining incomplete. Reject unrelated-table ratios and zero denominators. Preserve numerator, denominator, and formula; finite decimals use Decimal and repeating decimals exact fractions, never silent rounding.

Aggregation defaults to consistent source-supported complete declarations for all participating tables. To calculate only read scope, explicitly set `"require_complete":false` on group/count/ratio; partial results cannot satisfy complete slots. Never use Top-N for global statistics. Unknown-snapshot one/explicit-observed slots may confirm original batch values with observed status and a version/freshness limitation. Complete slots retain their version gap; do not join across versions or claim completeness.

## Executable synthetic example

Run from the skill directory. This fictional knowledge-object catalog needs no SDK or credentials and imposes no schema or status meanings on actual knowledge bases. The draft deliberately omits a second object, names/dates, and replaces the source state with an unsupported assertion.

Create a fresh private directory and file before writing business evidence. `mktemp` creates the directory with mode 0700 and the file with mode 0600; `umask 077` also protects any later artifacts created in this shell. Never reuse a predictable shared filename. Keep the exact paths returned by these commands: subsequent snippets use the same shell variables. Separate tool invocations usually start new shells, so explicitly pass the already-created private path between invocations rather than assuming the variables persist or deriving a path from retrieved content.

```sh
set -eu
umask 077
CONTEXT_GRAPH_JOB_DIR="$(mktemp -d "${TMPDIR:-/tmp}/context-graph-answer.XXXXXXXX")"
CONTEXT_GRAPH_JOB_FILE="$(mktemp "$CONTEXT_GRAPH_JOB_DIR/job.XXXXXXXX")"
cat > "$CONTEXT_GRAPH_JOB_FILE" <<'JSON'
{
  "schema": "context-graph-answer-job-v1",
  "context": {
    "batch_id": "synthetic-batch",
    "identity_scope": "synthetic-caller",
    "region": "cn-beijing",
    "KnowledgeBaseIds": [
      "synthetic-kb"
    ],
    "snapshot": "synthetic-v1"
  },
  "tables": [
    {
      "name": "objects",
      "primary_key": [
        "id"
      ],
      "response": {
        "Action": "GetKnowledgePoint",
        "Success": true,
        "RequestId": "synthetic-request",
        "Data": {
          "KnowledgeBaseId": "synthetic-kb",
          "Type": "WIKI",
          "Id": "synthetic-wiki",
          "Warnings": [],
          "Wiki": {
            "Title": "Synthetic knowledge-object catalog",
            "Content": "Complete synthetic list, version synthetic-v1.\n```tsv\nid\tdomain\tstate\teffective_until\tname\nA\texample-domain\tPublished\t2026-11-30\tdim_entity\nB\texample-domain\tDraft\t2026-12-01\tfact_event\n```"
          }
        }
      },
      "coverage": {
        "dataset": "synthetic-objects",
        "snapshot": "synthetic-v1",
        "row_count": 2,
        "basis": "Complete synthetic list, version synthetic-v1."
      }
    }
  ],
  "operations": [
    {
      "id": "published",
      "type": "select",
      "table": "objects",
      "where": {
        "state": "Published"
      }
    },
    {
      "id": "fraction",
      "type": "ratio",
      "numerator": "published",
      "denominator": "objects"
    }
  ],
  "contract": {
    "question_id": "synthetic-question",
    "question_type": "association",
    "required_slots": [
      {
        "name": "ids",
        "label": "Knowledge object IDs",
        "cardinality": "set",
        "format": "id"
      },
      {
        "name": "names",
        "label": "Knowledge object names",
        "cardinality": "set",
        "format": "text"
      },
      {
        "name": "dates",
        "label": "Version end dates",
        "cardinality": "set",
        "format": "date"
      },
      {
        "name": "state",
        "label": "A original state",
        "cardinality": "one",
        "format": "text"
      },
      {
        "name": "ratio",
        "label": "Published object ratio",
        "cardinality": "one",
        "format": "number"
      }
    ]
  },
  "bindings": {
    "ids": {
      "table": "objects",
      "column": "id",
      "where": {
        "domain": "example-domain"
      }
    },
    "names": {
      "table": "objects",
      "column": "name",
      "where": {
        "domain": "example-domain"
      }
    },
    "dates": {
      "table": "objects",
      "column": "effective_until",
      "where": {
        "domain": "example-domain"
      }
    },
    "state": {
      "table": "objects",
      "column": "state",
      "where": {
        "id": "A"
      }
    },
    "ratio": {
      "calculation": "fraction"
    }
  },
  "draft": {
    "ids": [
      "A"
    ],
    "names": [
      "dim_entity"
    ],
    "dates": [
      "2026-11-30"
    ],
    "state": [
      "ProductionReady"
    ],
    "ratio": []
  }
}
JSON
python3 -S scripts/answer_contract.py --input "$CONTEXT_GRAPH_JOB_FILE" --repair-rounds 2 --format json
python3 -S scripts/answer_contract.py --input "$CONTEXT_GRAPH_JOB_FILE" --repair-rounds 2 --format markdown
```

Both commands exit 0. JSON status is ready, resolved_count=5, and history retains the first repair; the second round stops on no progress. Markdown lists A/B, dim_entity/fact_event, both full dates, original Published, and ratio 0.5 with numerator 1/denominator 2, without a second lossy prose summary. The ratio describes only this fictional catalog and its explicit state filter, not data freshness, queryability, or an inferred business outcome.

Omit --repair-rounds 2 to inspect initial missing/extra differences (exit 3). Even when the draft says ProductionReady, Markdown displays only recomputed Published and draft gaps, never the unverified assertion as fact. Default business-facing Markdown uses labels, complete fields, and readable sources; internal slots, endpoint, opaque API IDs, and hashes remain in JSON audit. Add --include-diagnostics explicitly to show full Markdown audit data.

## Repair, statuses, and safety

repair_rounds accepts only 0/1/2. Repairs use deterministic expected values from this job, adding missing and removing extra values/slots. They make no requests, read no other evidence, and never guess ambiguities. Disclosed unknowns do not increase resolved_count. Reports preserve initial_issues, history, current unknown/missing/extra, and addressed/resolved counts. Ambiguous slots cannot become ready.

Every CLI run recomputes/renders the original job to stdout; it accepts no output-file path and overwrites no file. Exit codes: 0=ready (this contract's fields only), 2=invalid input/budget, 3=needs_repair, 4=incomplete (unknown/partial/version gaps), 5=observed (explicit read scope only). Handle differences or disclose scope for nonzero statuses; do not announce global completion.

The file entry point requires O_NONBLOCK and O_NOFOLLOW. If either is unavailable, fail safely with UnsupportedPlatform. Otherwise use nonblocking open, symlink rejection, and fstat to accept only bounded regular files, rejecting FIFOs/symlinks. Limits: 8 MiB input, depth 32, 300000 structure nodes, 10000 raw records/join results, 128 TSV blocks, 128 columns, 50 operations, and 16 MiB output including provenance. Duplicate-row sources count too. Check join rows and accumulated tables before expansion; union checks cumulative metadata, rows, and each added source before append rather than concatenating first. Answers accumulate per-slot/per-source budgets including initial_issues/history/draft; JSON iterencode counts chunks and stops at the limit instead of constructing huge temporary strings. Reject duplicate JSON keys, nonfinite numbers, and unknown job/context/operation/contract/binding structures. Errors use fixed safe messages/reason codes, never bad input or tracebacks. ZeroDenominator means undefined division; IncompleteAggregation means global computation is unconfirmed; SnapshotMismatch means unknown/inconsistent snapshots. Escape content/labels as literal Markdown to prevent fake links/HTML/instructions.

Sources retain full KB/Type/Id, RequestId, Title, content SHA256, physical start/end lines, column, and original primary key. Multiple blocks of the same body are allowed; mixed content versions are not. Empty tables retain table-level identity/hash. Source download links never enter results. There is no global disk cache or credential-valued cache key.

## Python interface

Only standard library and bundled context_graph_contract.py are required. Run from the skill directory with the private job path explicitly passed as an argument:

```sh
python3 -S - "$CONTEXT_GRAPH_JOB_FILE" <<'PY'
import sys

sys.path.insert(0, "scripts")
from evidence_tables import EvidenceError, load_job, build_evidence
from answer_contract import evaluate_job, render_markdown

job = load_job(sys.argv[1])
evidence = build_evidence(job)  # context/tables/calculations, without slot checks
report = evaluate_job(job, repair_rounds=2)  # context-graph-answer-report-v1
markdown = render_markdown(job, repair_rounds=2)  # recompute; reject self-declared pass reports
# markdown = render_markdown(job, repair_rounds=2, include_diagnostics=True)
print(markdown)
PY
```

Use evaluate_job as the unified Agent entry point: it always validates/recomputes the job. Public render_markdown also accepts only the original job; an invented pass report is rejected. The report renderer is private and the CLI calls it after one validation. This constrains recommended entry points, not arbitrary Python reflection/private-function calls. Each report.slots item contains name/label/cardinality/format/completeness, expected/missing/extra/unknown/resolved, sources, coverage_declarations, and an optional calculation summary (kind/formula; ratios also numerator/denominator/exact_decimal). Store provenance only in slot sources. build_evidence calculations.values contains exact string arrays; each group value is deterministic JSON with key/members/count, with structured groups also available. Answer expected retains complete group values; default Markdown renders every member without duplicating calculation.sources/groups. Callers need not guess fields.

After validation and answer delivery, remove only this run's private job and its now-empty directory using the original paths returned by `mktemp`. Do not clean up before later snippets have consumed the job, use recursive deletion, or accept cleanup paths from knowledge content. If other artifacts remain, `rmdir` fails instead of deleting them:

```sh
rm -- "$CONTEXT_GRAPH_JOB_FILE"
rmdir -- "$CONTEXT_GRAPH_JOB_DIR"
```
