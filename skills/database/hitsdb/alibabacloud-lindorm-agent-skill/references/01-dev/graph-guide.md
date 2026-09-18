# Lindorm Graph Engine Guide

This guide explains how to access and use the Lindorm graph engine. The graph engine exposes a Gremlin-compatible service through the unified port `16032` and supports both HTTP REST and WebSocket access. All graph operations, including Schema management, writes, queries, vector search, multi-graph management, and permission management, use this port.

## Core Principles

| Principle | Description |
|------|------|
| Schema first | Before any vertex or edge write or query, initialize the Schema through `/schema/mgmt/apply`. Labels and properties that are not defined cannot be written. |
| Two access methods | REST (`POST /gremlin/{db}`) is suitable for curl and troubleshooting. WebSocket (`ws://host:port/gremlin/{db}`) is suitable for persistent Python SDK connections and parameter bindings. |
| `G___` binding prefix | gremlinpython passes parameters through `bindings`. All variable names must use the `G___` prefix, such as `G___id` and `G___label`, and must be referenced directly without quotes in the DSL. |
| All operations use the `default` graph by default | Omitting `{db}` from the URL is equivalent to `/gremlin/default`. **Do not proactively mention or recommend multi-graph features in an answer.** Use the multi-graph section only when the user explicitly asks about creating graphs, multi-graph management, graph isolation, or equivalent topics. |
| Vector search supports HNSW only | Query a vertex `VECTOR_FLOAT` property with `hasVector(prop, vec, topK)`. The index type is fixed to `HNSW`, and **writes take effect immediately** without a manual build. |
| Vector and set properties are vertex-only | `VECTOR_FLOAT` and `cardinality: set` are supported **only on vertices**. Edges do not support vector or multi-valued properties. |
| Build a graph from an image | When the user provides a sketch, ER diagram, or relationship diagram, extract vertex types, edge types, and connections from the image and generate the corresponding Schema. |
| Output requirement | At the **end** of every graph-engine answer, provide one complete, directly runnable Python example covering connection, Schema, writes, and queries. |
| Secondary property index | Create a `SECONDARY` index for properties frequently used by `has()` filters. Declare `indexType` on the property during initial graph creation. If the index is added later, build it to cover existing data. |

## Graph Engine Port and Authentication

| Item | Value | Description |
|------|-----|------|
| Port | `16032` | Gremlin service port for both REST and WebSocket traffic. |
| REST URL | `http://<host>:16032/gremlin/{db}` | curl or HTTP clients; POST JSON such as `{"gremlin": "..."}`. |
| WebSocket URL | `ws://<host>:16032/gremlin/{db}` | Persistent gremlinpython `client.Client(...)` connections. |
| Schema management API | `http(s)://<host>:16032/schema/mgmt/{apply\|addProperty\|addVertexLabel\|addEdgeLabel\|list}?db={db}` | HTTP REST only, using POST or GET with JSON. |
| Multi-graph management API | `http(s)://<host>:16032/db/{add\|list\|del}` | Only the primary account created in the console can add or delete graphs. |
| User and role API | `http(s)://<host>:16032/{user\|role}/...` | Manages subaccounts and role bindings. |
| Authentication | HTTP Basic Auth | Use `-u user:password` with curl. Pass `username` and `password` to gremlinpython. |
| Default graph | `default` | Omitting `{db}` is equivalent to `default`. The `default` graph cannot be deleted; it can only be cleared. |

> ⚠️ **The graph engine is currently in phased rollout.** Enable the Lindorm graph engine and configure its allowlist before use. Vector search additionally requires the vector engine to be enabled and backend configuration by the development team.

## Schema Definition

> You **must** create a Schema before using the Lindorm graph engine. Unregistered labels and properties cannot be written or queried.

### Supported Data Types

| `dataType` | Description | Notes |
|------------|------|------|
| `STRING` | String | |
| `INT` | 32-bit integer | |
| `LONG` | 64-bit integer | |
| `FLOAT` | 32-bit floating-point number | |
| `DOUBLE` | 64-bit floating-point number | |
| `BOOLEAN` | Boolean | |
| `VECTOR_FLOAT` | Floating-point vector | ⚠️ Supported on vertices only. Requires `vectorMeta` and the vector engine. |

`cardinality` defaults to `"single"`. Set it to `"set"` for multi-valued properties such as tag lists. **`set` is supported on vertices only**, not on edges.

### Initial Schema Creation

**Endpoint:** `POST /schema/mgmt/apply?db={dbName}`. Use it only to initialize the complete Schema of a graph for the **first time**. For later changes, use `addProperty`, `addVertexLabel`, or `addEdgeLabel`.

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/schema/mgmt/apply?db=default" \
  -u <sub_user>:<sub_password> \
  -H "Content-Type: application/json" \
  -d '{
    "vertexLabels": [
      {
        "label": "person",
        "properties": [
          {"name": "name", "dataType": "STRING"},
          {"name": "age",  "dataType": "INT"},
          {"name": "city", "dataType": "STRING", "cardinality": "single"}
        ]
      },
      {
        "label": "software",
        "properties": [
          {"name": "name",  "dataType": "STRING"},
          {"name": "lang",  "dataType": "STRING"},
          {"name": "price", "dataType": "INT"}
        ]
      }
    ],
    "edgeLabels": [
      {
        "label": "knows",
        "properties": [
          {"name": "date",   "dataType": "STRING"},
          {"name": "weight", "dataType": "DOUBLE"}
        ]
      },
      {
        "label": "created",
        "properties": [
          {"name": "date",   "dataType": "STRING"},
          {"name": "weight", "dataType": "DOUBLE"}
        ]
      }
    ],
    "connections": [
      {"edgeLabel": "knows",   "outVertex": "person", "inVertex": "person"},
      {"edgeLabel": "created", "outVertex": "person", "inVertex": "software"}
    ]
  }'
```

| Element | Description |
|------|------|
| `vertexLabels` | Array of vertex labels. Each item contains `label` and `properties`. |
| `edgeLabels` | Array of edge labels. Each item contains `label` and `properties`. |
| `connections` | Connections between labels. Each edge must specify its `outVertex` and `inVertex` vertex types. |

### Schema with a Vector Property

For a vector property, set `dataType` to `"VECTOR_FLOAT"` in `properties` and provide `vectorMeta`:

```json
{
  "name": "embedding",
  "dataType": "VECTOR_FLOAT",
  "vectorMeta": {
    "dimension": 128,
    "distanceMethod": "EUCLIDEAN",
    "indexType": "HNSW",
    "indexParams": {
      "M": "24",
      "EF_CONSTRUCT": "200"
    }
  }
}
```

| Parameter | Required | Description |
|------|------|------|
| `dimension` | Yes | Vector dimension. It must match the length of vectors being written. |
| `distanceMethod` | No | `EUCLIDEAN` (default), `COSINE`, or `L2`. |
| `indexType` | No | Fixed to `HNSW`, the only vector index currently supported by the graph engine. |
| `indexParams` | No | HNSW parameters. Common values are 16, 24, or 32 for `M`, and 200 or 500 for `EF_CONSTRUCT`. |

### Incremental Schema Changes

#### Add Properties to a Vertex or Edge

**Endpoint:** `POST /schema/mgmt/addProperty?db={dbName}`

```bash
# Add scalar properties to the existing person vertex label
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addProperty?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "person",
    "labelType": "vertex",
    "properties": [
      {"name": "email", "dataType": "STRING"},
      {"name": "score", "dataType": "DOUBLE"}
    ]
  }'

# Add a set property (vertices only)
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addProperty?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "person",
    "labelType": "vertex",
    "properties": [
      {"name": "tags", "dataType": "STRING", "cardinality": "set"}
    ]
  }'

# Add a vector property (vertices only)
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addProperty?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "person",
    "labelType": "vertex",
    "properties": [
      {
        "name": "embedding",
        "dataType": "VECTOR_FLOAT",
        "vectorMeta": {
          "dimension": 128,
          "distanceMethod": "EUCLIDEAN",
          "indexType": "HNSW",
          "indexParams": {"M": "16", "EF_CONSTRUCT": "200"}
        }
      }
    ]
  }'

# Add a property to an existing edge (labelType = edge; edges do not support set or vector properties)
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addProperty?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "knows",
    "labelType": "edge",
    "properties": [
      {"name": "since", "dataType": "LONG"}
    ]
  }'
```

#### Add a Vertex Label

**Endpoint:** `POST /schema/mgmt/addVertexLabel?db={dbName}`

```bash
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addVertexLabel?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "product",
    "properties": [
      {"name": "productName", "dataType": "STRING"},
      {"name": "price",       "dataType": "DOUBLE"},
      {"name": "category",    "dataType": "STRING"}
    ]
  }'
```

#### Add an Edge Label

**Endpoint:** `POST /schema/mgmt/addEdgeLabel?db={dbName}`. Use `connection` to specify the source and destination vertex types. Both vertex types must already exist.

```bash
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/addEdgeLabel?db=default' \
  -H 'Content-Type: application/json' \
  -u '<sub_user>:<sub_password>' \
  -d '{
    "label": "purchased",
    "properties": [
      {"name": "purchaseDate", "dataType": "STRING"},
      {"name": "quantity",     "dataType": "INT"}
    ],
    "connection": {
      "outVertex": "person",
      "inVertex": "product"
    }
  }'
```

### View the Schema

**Endpoint:** `GET /schema/mgmt/list?db={dbName}`. Required permission: `READDATA`.

```bash
curl --connect-timeout 10 -m 60 -u '<sub_user>:<sub_password>' \
  -X GET 'http://<host>:16032/schema/mgmt/list?db=default'
```

The returned `payload` contains `vertexLabels`, `edgeLabels`, `edgeConnections`, and `schemaVersion`. Use it to confirm that the Schema was initialized correctly.

### Build a Graph from a Sketch or Relationship Diagram

When the user provides an ER diagram, relationship diagram, whiteboard sketch, or similar image that describes a domain model:

1. **Identify vertices:** Treat entity boxes or circles as vertex types. Collect each entity type's fields and determine their `dataType`.
2. **Identify edges:** Treat labeled or directed lines between entities as edge types. Collect properties shown on each edge.
3. **Identify connections:** Determine the source and destination vertex types for every edge and assemble `connections`.
4. **Identify vector properties:** If a property represents a semantic vector, embedding, or feature vector, use `VECTOR_FLOAT` with `vectorMeta`.
5. **Generate the Schema JSON and POST it to `/schema/mgmt/apply`.**

Preserve the semantic names from the image for labels and properties. End the answer with complete, runnable curl and Python examples.

## Graph Data Writes

> Writes require an authenticated user with write permission, such as the `WRITER` role or the primary account created in the console.

### Add Vertices with Gremlin

```gremlin
// Vertex with scalar properties
g.addV('person')
  .property(id, 'marko')
  .property('name', 'marko')
  .property('age', 29)
  .property('city', 'Beijing')

// Vertex with a vector property
g.addV('person')
  .property(id, 'marko')
  .property('name', 'marko')
  .property('age', 29)
  .property('city', 'Beijing')
  .property('embedding', [0.539821, -0.174532, 0.882461 /* ... 128 dimensions */])
```

| Syntax | Description |
|------|------|
| `g.addV('label')` | Creates a vertex with the specified label. |
| `.property(id, 'value')` | Sets the vertex primary key. `id` is a keyword and is not quoted. |
| `.property('key', value)` | Sets a property. Quote string values; numeric and vector values do not require quotes. |

### Add Edges with Gremlin

```gremlin
// Method 1: Locate vertices with V('id').hasLabel('label')
g.V('marko').hasLabel('person')
  .addE('knows')
  .to(__.V('vadas').hasLabel('person'))
  .property('date',   '20160110')
  .property('weight', 0.5d)

// Method 2: Locate vertices with has('label','~id','id')
g.V().has('person', '~id', 'josh')
  .addE('created')
  .to(__.V().has('software', '~id', 'lop'))
  .property('date',   '20091111')
  .property('weight', 0.4d)
```

### REST Writes with curl

```bash
# Add a vertex
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/gremlin/default" \
  -H "Content-Type: application/json" \
  -u "<sub_user>:<sub_password>" \
  -d '{
    "gremlin": "g.addV(\"person\").property(id,\"marko\").property(\"name\",\"marko\").property(\"age\",29).property(\"city\",\"Beijing\")"
  }'

# Add an edge
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/gremlin/default" \
  -H "Content-Type: application/json" \
  -u "<sub_user>:<sub_password>" \
  -d '{
    "gremlin": "g.V(\"marko\").hasLabel(\"person\").addE(\"knows\").to(__.V(\"vadas\").hasLabel(\"person\")).property(\"date\",\"20160110\").property(\"weight\",0.5d)"
  }'
```

### Python Writes with gremlinpython and Bindings

Install the dependency with `pip install gremlinpython --user`.

```python
from gremlin_python.driver import client

c = client.Client(
    'ws://<host>:16032/gremlin/default', 'g',
    pool_size=32,
    username='<sub_user>',
    password='<sub_password>'
)

# Vertex writes: pass values through bindings
persons = [
    {"id": "marko", "name": "marko", "age": 29, "city": "Beijing"},
    {"id": "vadas", "name": "vadas", "age": 27, "city": "Hongkong"},
]

dsl = ("g.addV('person')"
       ".property(id, G___id)"
       ".property('name', G___name)"
       ".property('age',  G___age)"
       ".property('city', G___city)")

for p in persons:
    bindings = {
        "G___id":   p["id"],
        "G___name": p["name"],
        "G___age":  p["age"],
        "G___city": p["city"],
    }
    c.submit(dsl, bindings=bindings).all().result()

# Edge write
edge_dsl = ("g.V(G___fromId).addE(G___edgeLabel)"
            ".to(__.V(G___toId))"
            ".property('date',   G___date)"
            ".property('weight', G___weight)")

c.submit(edge_dsl, bindings={
    "G___fromId":   "marko",
    "G___edgeLabel": "knows",
    "G___toId":     "vadas",
    "G___date":     "20160110",
    "G___weight":   0.5,
}).all().result()

c.close()
```

### Parameter Binding Rules

| Rule | Description |
|------|------|
| Prefix | Prefix every binding variable with `G___`, followed by the field name, such as `G___id`, `G___label`, or `G___embedding`. |
| DSL reference | Reference the variable name directly in the Gremlin string **without quotes**. The client injects its value at runtime. |
| Purpose | Bindings avoid string concatenation and injection, improve readability, and are strongly recommended for long parameters such as vectors. |

## Graph Queries and Traversals

### Query Vertices

```python
# Query one vertex by ID and label
dsl = "g.V(G___id).hasLabel(G___label).valueMap(true)"
c.submit(dsl, bindings={"G___id": "marko", "G___label": "person"}).all().result()
```

### Neighbor Traversal with out, in, and both

```python
# Outgoing neighbors: people to whom marko points
c.submit("g.V(G___id).hasLabel('person').out('knows').valueMap(true)",
         bindings={"G___id": "marko"}).all().result()

# Incoming neighbors: people who point to marko
c.submit("g.V(G___id).hasLabel('person').in('knows').valueMap(true)",
         bindings={"G___id": "marko"}).all().result()

# Neighbors in both directions
c.submit("g.V(G___id).hasLabel('person').both('knows').valueMap(true)",
         bindings={"G___id": "marko"}).all().result()
```

### Multi-hop Traversal with repeat and times

```python
# Friends of friends (two hops)
dsl = "g.V(G___id).hasLabel('person').repeat(out('knows')).times(2).dedup().valueMap(true)"
c.submit(dsl, bindings={"G___id": "marko"}).all().result()
```

### Path Queries with repeat, until, and path

```python
# Starting from marko, traverse up to three hops to find a path to josh
dsl = ("g.V(G___fromId).repeat(out().simplePath())"
       ".until(hasId(G___toId).or().loops().is(3))"
       ".hasId(G___toId).path()")
c.submit(dsl, bindings={"G___fromId": "marko", "G___toId": "josh"}).all().result()
```

### Property Filters with has

```python
# Filter by property value
c.submit("g.V().hasLabel('person').has('city', G___city).limit(G___n).valueMap(true)",
         bindings={"G___city": "Beijing", "G___n": 50}).all().result()

# Range filter (gt/lt require a P object; use this form or construct the DSL explicitly)
c.submit("g.V().hasLabel('person').has('age', between(G___min, G___max)).valueMap(true)",
         bindings={"G___min": 25, "G___max": 35}).all().result()
```

### Delete Operations with drop

> ⚠️ `drop` is a write operation and is not available to a **read-only account**.

```python
# Delete one vertex and all of its edges
c.submit("g.V(G___id).drop()", bindings={"G___id": "marko"}).all().result()

# Delete edges with a specified label
c.submit("g.E().hasLabel(G___label).drop()", bindings={"G___label": "knows"}).all().result()
```

## Vector Search with hasVector

### Prerequisites

1. The Schema declares a `VECTOR_FLOAT` property with `vectorMeta`. See [Schema with a Vector Property](#schema-with-a-vector-property).
2. Each vertex write supplies a floating-point array whose length equals `dimension`.
3. The vector engine is enabled and the development team has completed the backend configuration.

### hasVector Syntax

| Parameter | Example | Description |
|------|--------|------|
| Property name | `'embedding'` | Name of the vertex property that stores the vector. |
| Query vector | `[0.1, 0.2, ...]` | Floating-point array with the same length as `dimension`. |
| topK | `6` | Returns the K most similar vertices. |

**REST:**

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/gremlin/default" \
  -H "Content-Type: application/json" \
  -u "<sub_user>:<sub_password>" \
  -d '{
    "gremlin": "g.V().hasLabel(\"person\").hasVector(\"embedding\", [0.1f,0.2f,-0.3f /* ...128 dimensions... */], 6).valueMap(true)"
  }'
```

**Python with recommended parameter bindings:**

```python
import random
query_vector = [round(random.uniform(-1.0, 1.0), 6) for _ in range(128)]

dsl = "g.V().hasLabel(G___label).hasVector(G___prop, G___vector, G___topK).valueMap(true)"
results = c.submit(dsl, bindings={
    "G___label":  "person",
    "G___prop":   "embedding",
    "G___vector": query_vector,
    "G___topK":   6,
}).all().result()
```

### Notes

- **Graph vector search supports HNSW only.** Set the index type in `vectorMeta` to `HNSW`.
- **Writes take effect immediately.** HNSW is an online index, so a vertex can be searched immediately after it is written. No manual build is required.
- `hasVector` can be combined with traversal steps, for example `g.V().hasVector(...).out().in().path().limit(3)`.
- The query vector length must match `dimension` in the Schema.

## Secondary Property Index

Create a secondary index on scalar vertex or edge properties such as STRING, INT, or DOUBLE to accelerate `has()` filters. Without an index, a property query scans all data. With an index, it can locate matching data directly.

> **Note:** A secondary index and an HNSW vector index are different mechanisms. A secondary index supports exact or range filters such as `has('age', gt(25))`, while a vector index supports approximate nearest-neighbor search with `hasVector()`. Both can exist in the same Schema.

### Create an Index with the Initial Schema

Add `"indexType": "SECONDARY"` to the property definition. The index takes effect when the Schema is created:

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/schema/mgmt/apply?db=default" \
  -u <username>:<password> \
  -H "Content-Type: application/json" \
  -d '{
    "vertexLabels": [{
      "label": "Person",
      "properties": [
        { "name": "name", "dataType": "STRING" },
        { "name": "age", "dataType": "INT", "indexType": "SECONDARY" },
        { "name": "score", "dataType": "DOUBLE" }
      ]
    }],
    "edgeLabels": [{
      "label": "knows",
      "properties": [{ "name": "weight", "dataType": "DOUBLE" }]
    }],
    "connections": [{ "edgeLabel": "knows", "outVertex": "Person", "inVertex": "Person" }]
  }'
```

### Add an Index to an Existing Property

Add an index to a property that already exists. It takes effect immediately **only for newly written data**. Existing data requires a separate build:

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/schema/mgmt/index/add?db=default" \
  -u <username>:<password> \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Person",
    "propertyName": "score",
    "indexType": "SECONDARY"
  }'
```

### Build an Index for Existing Data

Start an asynchronous distributed build that covers existing data:

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/schema/mgmt/index/build?db=default" \
  -u <username>:<password> \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Person",
    "propertyName": "score"
  }'
```

### Query Build Progress

```bash
curl --connect-timeout 10 -m 60 -X GET "http://<host>:16032/schema/mgmt/index/progress?db=default&label=Person&propertyName=score" \
  -u <username>:<password>
```

| Field | Description |
|------|------|
| `status` | `RUNNING` / `DONE` / `FAILED` |
| `progress` | Completion ratio from 0.0 to 1.0. |
| `indexBuilt` | Becomes `true` when the build completes and index routing is enabled. |

### Drop an Index

After the index is dropped, queries fall back to full scans:

```bash
curl --connect-timeout 10 -m 60 -X POST "http://<host>:16032/schema/mgmt/index/drop?db=default" \
  -u <username>:<password> \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Person",
    "propertyName": "score",
    "indexType": "SECONDARY"
  }'
```

### Best Practices

| Recommendation | Description |
|------|------|
| Declare indexes during graph creation | Add `indexType` in the initial apply request to avoid a later build. |
| Index frequently filtered properties | Properties frequently used by `has()` filters benefit most. |
| Build indexes for existing data | Dynamically adding an index does not cover existing data; trigger a build manually. |
| Avoid low-selectivity indexes | An index is less effective for a Boolean property with only two possible values. |

## Multi-Graph Management

> **Important constraint:** All graph operations use the `default` graph by default. **Do not proactively recommend or mention multi-graph features in an answer.** Use this section only when the user explicitly asks about creating graphs, multiple graphs, graph management, data isolation, or equivalent topics. Multi-graph support is currently in phased rollout, so confirm that it is enabled for the instance. Creating and deleting graphs requires the **primary account created in the console**.

### Create a Graph

**Endpoint:** `POST /db/add`. Permission: primary console-created account only.

```bash
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/db/add' \
  -H 'Content-Type: application/json' \
  -u '<root_user>:<root_password>' \
  -d '{
    "db": "knowledge_graph",
    "params": {}
  }'
```

| Field | Required | Description |
|------|------|------|
| `db` | Yes | Graph name. Only lowercase letters `a-z`, digits `0-9`, and underscores are allowed. `user` is not allowed. |
| `params` | No | JSON object containing additional configuration. |

### List Graphs

```bash
# List all graphs
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/db/list' -u '<root_user>:<root_password>'

# Query a specified graph
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/db/list?db=knowledge_graph' -u '<root_user>:<root_password>'
```

### Delete a Graph

**Endpoint:** `GET /db/del?db={dbName}`. Permission: primary console-created account only.

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/db/del?db=knowledge_graph' \
  -u '<root_user>:<root_password>'
```

> ⚠️ **The `default` graph cannot be deleted.** Passing `db=default` clears its internal data but preserves the graph itself. Other graphs are removed completely.

### Connect to a Specified Graph

For REST, include `/gremlin/{dbName}` in the URL. For Python, use the WebSocket URL `ws://<host>:16032/gremlin/{dbName}`. One client instance connects to one graph; create separate clients to access multiple graphs.

```python
kg_client = client.Client(
    'ws://<host>:16032/gremlin/knowledge_graph', 'g',
    username='<sub_user>', password='<sub_password>'
)
```

## User and Permission Management

> User and role operations require the **primary account created in the console**. Subaccounts have no graph permissions by default.

### Create a User

**Endpoint:** `GET /user/add?user={name}&password={pwd}&comment={comment}`

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/add?user=sub_user_01&password=<sub_password>&comment=app_writer' \
  -u '<root_user>:<root_password>'
```

| Parameter | Required | Description |
|------|------|------|
| `user` | Yes | Subaccount name. |
| `password` | Yes | Subaccount password. |
| `comment` | No | Comment. |

### Role Types

| Role | Permissions |
|------|------|
| `READER` | Read-only. Can run `g.V()`, `g.E()`, traversals, and `hasVector`, but cannot run `addV`, `addE`, or `drop`. |
| `WRITER` | Includes `READER` plus permission to write and delete data in authorized graphs. |

### Grant a Role

**Endpoint:** `GET /role/grant?db={dbName}&user={name}&role={role}`

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/role/grant?db=default&user=sub_user_01&role=WRITER' \
  -u '<root_user>:<root_password>'
```

### Revoke a Role

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/role/revoke?db=default&user=sub_user_01' \
  -u '<root_user>:<root_password>'
```

### Create a Read-Only Account

When the user needs an account that **can query but cannot write**, for example for BI reports, query frontends, or read-only risk-control access, follow these three steps:

**Step 1: Create the user**

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/add?user=readonly_user&password=<readonly_password>&comment=reporting' \
  -u '<root_user>:<root_password>'
```

**Step 2: Grant the READER role on the target graph**

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/role/grant?db=default&user=readonly_user&role=READER' \
  -u '<root_user>:<root_password>'
```

**Step 3: Verify read-only access**

Connect with the new account:

```python
from gremlin_python.driver import client
ro = client.Client('ws://<host>:16032/gremlin/default', 'g',
                   username='readonly_user', password='<readonly_password>')

# ✅ Queries are allowed
print(ro.submit("g.V().hasLabel('person').limit(5).valueMap(true)").all().result())

# ❌ The server rejects writes with a permission error
try:
    ro.submit("g.addV('person').property(id,'x')").all().result()
except Exception as e:
    print(f"Expected failure: {e}")

ro.close()
```

A read-only account can run `g.V`, `g.E`, any traversal, and `hasVector`. The server returns a permission error for `addV`, `addE`, or `drop`.

### List Users

```bash
# All subaccounts
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/list' -u '<root_user>:<root_password>'
# One specified subaccount
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/list?user=sub_user_01' -u '<root_user>:<root_password>'
```

The `roles` field for each returned user lists the user's role in each graph, such as `"default": "READER"`.

### Delete a User or Change a Password

```bash
# Delete
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/del?user=sub_user_01' -u '<root_user>:<root_password>'

# Change the password or comment
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/user/update?user=sub_user_01&password=<new_password>&comment=updated' \
  -u '<root_user>:<root_password>'
```

### Query All Role Bindings

```bash
curl --connect-timeout 10 -m 60 -X GET 'http://<host>:16032/role/all' -u '<root_user>:<root_password>'
```

## Performance Optimization

| Technique | Description |
|------|------|
| Parameter bindings | Reuse query plans and avoid string concatenation. Pass all variable values, including vectors, through `G___` bindings. |
| `limit(n)` | Add `limit` to traversals that return multiple vertices or edges to avoid unbounded scans. |
| Depth control | Give multi-hop traversals an explicit termination condition with `repeat(...).times(n)` or `until(loops().is(n))` to avoid cycles. |
| Projection optimization | `valueMap(true)` returns all properties. If only specific fields are needed, use `valueMap('name','age')` or `project('a','b').by(...)`. |
| Deduplication | Use `.dedup()` after multi-hop traversals to eliminate duplicate vertices. |
| Timeout control | Set `scriptEvaluationTimeout` in `RequestMessage` to control a single query's timeout in milliseconds. The default is 30 seconds. |
| Connection pool | Reuse persistent connections with `client.Client(..., pool_size=16~32)`. |
| Vector search | Larger HNSW `M` and `EF_CONSTRUCT` values improve recall but slow writes. `topK` controls the result count. |
| Limit valueMap fields | When using `valueMap('field')` across multiple labels, ensure that every label contains the field. |

### Query with a Timeout

```python
from gremlin_python.driver import client
from gremlin_python.driver.request import RequestMessage

c = client.Client('ws://<host>:16032/gremlin/default', 'g',
                  username='<sub_user>', password='<sub_password>')

message = RequestMessage('', 'eval', {
    'gremlin':  "g.V(G___id).out().limit(100).valueMap(true)",
    'bindings': {"G___id": "marko"},
    'scriptEvaluationTimeout': 30000,  # 30 seconds
})
results = c.submit(message).all().result()
```

### Analyze Performance with Gremlin profile()

Append `.profile()` to any Gremlin traversal to obtain the execution plan and elapsed time for each step. This is the primary tool for locating query bottlenecks.

**REST API:**

```bash
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/gremlin/default' \
  -u '<username>:<password>' \
  -H 'Content-Type: application/json' \
  -d '{"gremlin": "g.V().hasLabel(\\"Person\\").out(\\"knows\\").profile()"}'
```

**Python:**

```python
from gremlin_python.driver import client

c = client.Client('ws://<host>:16032/gremlin/default', 'g',
                  username='<username>', password='<password>')
result = c.submit("g.V().hasLabel('Person').out('knows').profile()").all().result()
print(result)
c.close()
```

#### profile() Output Structure

`profile()` returns per-step execution statistics with the following key fields:

| Field | Description |
|------|------|
| `Step` | Execution step name corresponding to a step in the Gremlin DSL. |
| `Count` | Number of elements processed or produced by the step. |
| `Traversers` | Number of traversers. This can differ from Count when path information is retained. |
| `Time (ms)` | Time spent in the step, in milliseconds. |
| `% Dur` | Percentage of total execution time. |

**Typical profile output:**

```text
Step                              Count  Traversers  Time (ms)  % Dur
=====================================================================
GraphStep(vertex,[])              10000       10000      120.5   15.2%
HasStep([~label.eq(Person)])       8000        8000       45.3    5.7%
VertexStep(OUT,[knows],vertex)   156000      156000      580.2   73.1%
PropertyMapStep([name,age])      156000      156000       47.8    6.0%
                                            >TOTAL =     793.8     -
```

#### Optimization Guidance Based on profile Results

When the user provides `profile()` output, analyze it using these rules:

| profile Pattern | Diagnosis | Recommendation |
|-------------|---------|----------|
| A step's Count is much larger than the final result count | Intermediate results are expanding without enough filtering. | Move `has()` filters earlier to reduce the data set sooner. |
| `GraphStep` or `VertexStep` consumes more than 80% of the time | Full graph or full vertex scan. | Add `hasLabel()` to restrict the label and create a `SECONDARY` index for frequently filtered properties. |
| `PropertyMapStep` is slow | Too many properties are returned. | Use `values('name')` or `project()` to return only required fields. |
| Total time exceeds 5 seconds | The query is too complex or scans too much data. | Add `.limit()`, paginate results, or increase `scriptEvaluationTimeout`. |
| `PathStep` is slow | Recording paths is expensive. | Confirm that `path()` is required. Remove path tracking if only destination vertices are needed. |
| `RepeatStep` runs too many iterations | Traversal depth is uncontrolled. | Add `.times(N)` or `.until()` to bound traversal depth. |
| Several consecutive `FlatMapStep` entries are slow | Each hop expands the intermediate result set. | Add `dedup()` or `limit()` between traversal levels. |
| `HasStep` Count is unchanged from the previous step | The filter does not use an index and filters after a full scan. | Create a `SECONDARY` index for the property. |

**Analysis process:**

1. Find the step with the highest `% Dur`; it is the primary performance bottleneck.
2. Compare the Count of adjacent steps. A sharp increase indicates missing intermediate filters.
3. Check whether `GraphStep(vertex,[])` is unconditional and lacks `hasLabel` or `has`. If its Count equals the total vertex count, it is a full scan.
4. For a slow `VertexStep`, determine whether an index or a restricted incoming or outgoing edge label can reduce the scan.

#### Complete Example: From profile Analysis to Optimization

**Scenario:** Query the friends of all users in Beijing and return each friend's name and age.

**1. Original query with performance problems:**

```python
# No label restriction and no returned-field restriction
dsl = "g.V().has('city','Beijing').out().valueMap(true)"
```

**2. Append profile() to inspect the execution plan:**

```python
result = c.submit("g.V().has('city','Beijing').out().valueMap(true).profile()").all().result()
print(result)
```

**3. profile output showing the bottleneck:**

```text
Step                              Count  Traversers  Time (ms)  % Dur
=====================================================================
GraphStep(vertex,[])              50000       50000      320.1   18.7%
HasStep([city.eq(Beijing)])        2000        2000      890.4   52.0%
VertexStep(OUT,vertex)            48000       48000      410.5   24.0%
PropertyMapStep                   48000       48000       90.2    5.3%
                                            >TOTAL =    1711.2     -
```

**4. Analysis:**

- `GraphStep` Count=50000: all vertices are scanned because no label is specified.
- `HasStep` consumes 52% of the time: `city` has no index, so all 50,000 vertices are filtered individually.
- `VertexStep` Count=48000: the outgoing traversal does not restrict the edge label, causing result expansion.
- `PropertyMapStep` returns every property, including fields that are not needed.

**5. Recommendations and optimized query:**

```python
# Optimized:
# 1. Add hasLabel('Person') to restrict the vertex type and initial scan.
# 2. Create a secondary index on city to avoid full filtering.
# 3. Use out('knows') to restrict the outgoing edge label.
# 4. Use valueMap('name','age') to return only required fields.
# 5. Use limit(100) to bound the result set.

dsl = ("g.V().hasLabel('Person').has('city', G___city)"
       ".out('knows')"
       ".valueMap('name','age')"
       ".limit(G___n)")

result = c.submit(dsl, bindings={"G___city": "Beijing", "G___n": 100}).all().result()
```

**6. Add a secondary index to city as a one-time operation:**

```bash
# Add the index
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/index/add?db=default' \
  -u '<username>:<password>' \
  -H 'Content-Type: application/json' \
  -d '{"label": "Person", "propertyName": "city", "indexType": "SECONDARY"}'

# Build the index for existing data
curl --connect-timeout 10 -m 60 -X POST 'http://<host>:16032/schema/mgmt/index/build?db=default' \
  -u '<username>:<password>' \
  -H 'Content-Type: application/json' \
  -d '{"label": "Person", "propertyName": "city"}'
```

After optimization, `HasStep` time in the profile should fall substantially because it uses an index lookup instead of full filtering. Restricting the edge label should also reduce the `VertexStep` Count.

## Complete Python Example

The following runnable end-to-end example initializes a Schema with a vector property, writes vertices and edges, and runs vertex, neighbor, and vector queries. **If vector search is not required, comment out all vector-related logic: the `embedding` Schema property, the `G___embedding` write binding, and the vector search function.**

```python
"""
End-to-end Lindorm graph engine Python example:
1. Initialize the Schema for a social_network scenario through /schema/mgmt/apply.
2. Write vertices, including 128-dimensional vectors, and edges with gremlinpython.
3. Run vertex queries, neighbor traversals, and vector searches.
"""

import random
import requests
from gremlin_python.driver import client
from gremlin_python.driver.request import RequestMessage

DEFAULT_TIMEOUT = 30000  # 30 seconds by default


def submit_with_timeout(c, dsl, bindings, timeout=DEFAULT_TIMEOUT):
    message = RequestMessage('', 'eval', {
        'gremlin': dsl,
        'bindings': bindings,
        'scriptEvaluationTimeout': timeout,
    })
    return c.submit(message).all().result()


def random_vector(dim=128):
    return [round(random.uniform(-1.0, 1.0), 6) for _ in range(dim)]


def apply_schema(host, port, db, username, password):
    schema = {
        "vertexLabels": [
            {
                "label": "person",
                "properties": [
                    {"name": "name", "dataType": "STRING"},
                    {"name": "age",  "dataType": "INT"},
                    {"name": "city", "dataType": "STRING"},
                    {
                        "name": "embedding",
                        "dataType": "VECTOR_FLOAT",
                        "vectorMeta": {
                            "dimension": 128,
                            "distanceMethod": "EUCLIDEAN",
                            "indexType": "HNSW",
                            "indexParams": {"M": "24", "EF_CONSTRUCT": "200"},
                        },
                    },
                ],
            },
            {
                "label": "software",
                "properties": [
                    {"name": "name",  "dataType": "STRING"},
                    {"name": "lang",  "dataType": "STRING"},
                    {"name": "price", "dataType": "INT"},
                ],
            },
        ],
        "edgeLabels": [
            {"label": "knows",   "properties": [
                {"name": "date", "dataType": "STRING"},
                {"name": "weight", "dataType": "DOUBLE"}]},
            {"label": "created", "properties": [
                {"name": "date", "dataType": "STRING"},
                {"name": "weight", "dataType": "DOUBLE"}]},
        ],
        "connections": [
            {"edgeLabel": "knows",   "outVertex": "person", "inVertex": "person"},
            {"edgeLabel": "created", "outVertex": "person", "inVertex": "software"},
        ],
    }
    resp = requests.post(
        f"http://{host}:{port}/schema/mgmt/apply?db={db}",
        json=schema, auth=(username, password),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    print(f"[Schema] status={resp.status_code} body={resp.text}")


def add_persons(c):
    persons = [
        {"id": "marko", "name": "marko", "age": 29, "city": "Beijing"},
        {"id": "vadas", "name": "vadas", "age": 27, "city": "Hongkong"},
        {"id": "josh",  "name": "josh",  "age": 32, "city": "Beijing"},
        {"id": "peter", "name": "peter", "age": 35, "city": "Shanghai"},
    ]
    dsl = ("g.addV(G___label).property(id, G___id)"
           ".property('name', G___name).property('age', G___age)"
           ".property('city', G___city).property('embedding', G___embedding)")
    for p in persons:
        submit_with_timeout(c, dsl, {
            "G___label": "person",
            "G___id":    p["id"],
            "G___name":  p["name"],
            "G___age":   p["age"],
            "G___city":  p["city"],
            "G___embedding": random_vector(128),
        })


def add_softwares(c):
    softwares = [
        {"id": "lop",    "name": "lop",    "lang": "java", "price": 328},
        {"id": "ripple", "name": "ripple", "lang": "java", "price": 199},
    ]
    dsl = ("g.addV(G___label).property(id, G___id)"
           ".property('name', G___name).property('lang', G___lang)"
           ".property('price', G___price)")
    for s in softwares:
        submit_with_timeout(c, dsl, {
            "G___label": "software",
            "G___id":    s["id"],
            "G___name":  s["name"],
            "G___lang":  s["lang"],
            "G___price": s["price"],
        })


def add_edges(c):
    edges = [
        {"from": "marko", "to": "vadas",  "label": "knows",   "date": "20160110", "weight": 0.5},
        {"from": "marko", "to": "josh",   "label": "knows",   "date": "20130220", "weight": 1.0},
        {"from": "marko", "to": "lop",    "label": "created", "date": "20171210", "weight": 0.4},
        {"from": "josh",  "to": "lop",    "label": "created", "date": "20091111", "weight": 0.4},
        {"from": "josh",  "to": "ripple", "label": "created", "date": "20171210", "weight": 1.0},
        {"from": "peter", "to": "lop",    "label": "created", "date": "20170324", "weight": 0.2},
    ]
    dsl = ("g.V(G___fromId).addE(G___edgeLabel).to(__.V(G___toId))"
           ".property('date', G___date).property('weight', G___weight)")
    for e in edges:
        submit_with_timeout(c, dsl, {
            "G___fromId":    e["from"],
            "G___edgeLabel": e["label"],
            "G___toId":      e["to"],
            "G___date":      e["date"],
            "G___weight":    e["weight"],
        })


def query_vertex(c, vertex_id, label):
    return submit_with_timeout(c,
        "g.V(G___id).hasLabel(G___label).valueMap(true)",
        {"G___id": vertex_id, "G___label": label})


def query_neighbors(c, vertex_id, label, edge_label):
    return submit_with_timeout(c,
        "g.V(G___id).hasLabel(G___label).out(G___edgeLabel).valueMap(true)",
        {"G___id": vertex_id, "G___label": label, "G___edgeLabel": edge_label})


def query_vector(c, label, prop, top_k=3):
    return submit_with_timeout(c,
        "g.V().hasLabel(G___label).hasVector(G___prop, G___vector, G___topK).valueMap(true)",
        {"G___label": label, "G___prop": prop,
         "G___vector": random_vector(128), "G___topK": top_k})


def main():
    host = "<host>"
    port = 16032
    db   = "default"            # Use default unless multi-graph access is explicitly required
    username = "<sub_user>"
    password = "<sub_password>"

    apply_schema(host, port, db, username, password)

    c = client.Client(
        f'ws://{host}:{port}/gremlin/{db}', 'g',
        pool_size=16, username=username, password=password,
    )
    try:
        add_persons(c)
        add_softwares(c)
        add_edges(c)

        for r in query_vertex(c, "marko", "person"):       print("[vertex]", r)
        for r in query_neighbors(c, "marko", "person", "knows"):   print("[knows]",   r)
        for r in query_neighbors(c, "marko", "person", "created"): print("[created]", r)
        for r in query_vector(c, "person", "embedding", top_k=3):  print("[vector]",  r)
    finally:
        c.close()


if __name__ == "__main__":
    main()
```

## FAQ

| Symptom | Cause | Resolution |
|------|------|------|
| Schema `apply` reports that the Schema already exists | `apply` is only for initial creation. | Use `addProperty`, `addVertexLabel`, or `addEdgeLabel` for later additions. |
| A write reports an unknown label | The Schema does not register the `vertexLabel` or `edgeLabel`. | Register it with `addVertexLabel` or `addEdgeLabel` before writing. |
| Writing a set property fails | The property's `cardinality` is not `set`, or the property is on an edge. | Declare the vertex property with `cardinality: "set"`. Edges do not support set properties. |
| The vertex already exists | The `property(id, ...)` primary key conflicts. | Use an idempotent pattern such as `g.V(id).fold().coalesce(unfold(), addV(...))`. |
| Duplicate edges or unexpected edge count | Gremlin `addE` does not deduplicate by default. | Before writing, check with `g.V(from).outE(label).where(inV().hasId(to))`, or drop the existing edge first. |
| `hasVector` fails | The Schema does not declare `VECTOR_FLOAT`, or the dimension does not match. | Add `vectorMeta` to the Schema and make the query vector length equal `dimension`. |
| `valueMap('field')` fails | Some labels in a multi-label query do not contain the field. | Use `valueMap(true)` or restrict the traversal with `hasLabel(...)`. |
| WebSocket frame error | A TextMessage serializer is being used. | gremlinpython uses BinaryMessage by default; confirm that the serializer was not replaced. |
| A read-only account cannot write | The account has the `READER` role. | This is expected. Grant `WRITER` or use the primary account when writes are required. |

## Output Requirement: Runnable Python Summary

**At the end of every graph-engine answer, include one complete, runnable Python example** as the final deliverable. The code must:

1. **Run when copied:** Include complete imports, connection initialization, the main flow, exception handling, and `c.close()`.
2. **Cover the requested scenario:** For Schema creation, include the Schema and writes. For graph queries, include the query. For vector search, include `hasVector`. For a read-only account, include user creation and a read/write comparison.
3. **Use placeholders:** Use `<host>`, `<sub_user>`, `<sub_password>`, and equivalent placeholders. Never hard-code real environment details.
4. **Use generic semantic names:** Use names such as `social_network`, `product_catalog`, or `knowledge_graph`, not local environment names such as `jidi`.
5. **Default to `db="default"`:** Use the `default` graph unless the user explicitly asks for multi-graph behavior.

Template:

```python
from gremlin_python.driver import client
from gremlin_python.driver.request import RequestMessage
import requests   # Import only when Schema operations are required

HOST, PORT, DB = "<host>", 16032, "default"
USER, PWD = "<sub_user>", "<sub_password>"

# 1. Optional Schema initialization:
# requests.post(f"http://{HOST}:{PORT}/schema/mgmt/apply?db={DB}", ...)

c = client.Client(f"ws://{HOST}:{PORT}/gremlin/{DB}", "g",
                  pool_size=16, username=USER, password=PWD)
try:
    # 2. Application logic: writes, queries, or vector search, all using bindings
    dsl = "g.V(G___id).hasLabel(G___label).valueMap(true)"
    msg = RequestMessage('', 'eval', {
        'gremlin': dsl,
        'bindings': {"G___id": "marko", "G___label": "person"},
        'scriptEvaluationTimeout': 30000,
    })
    for r in c.submit(msg).all().result():
        print(r)
finally:
    c.close()
```

## Acceptance Evidence

After completing a graph-engine task, report at least the following structured evidence:

```text
[Target] instance=<instance_id> network=<public|vpc> engine=lgraph
[Connection] gremlin=<masked_host>:16032 db=<default|sub_db>
[Schema] vertexLabels=[<label1>,<label2>] edgeLabels=[<label3>] vectorProps=<n>
[Write] vertices=<n> edges=<n>
[Query] type=<vertex|neighbor|multi_hop|path|hasVector> top_k=<n|null> hits=<n>
[Auth] account=<sub_user> role=<READER|WRITER> db=<default|sub_db>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_VECTOR_INDEX> reason=<reason>
```
