# Supported One-Way Synchronization Links

Treat the matrices below as the complete set of links supported for creation. Every link is a same-account, one-way `SYNC` job. Rows represent sources, columns represent destinations, and `✓` marks a registered link. Before credential setup, database connection testing, price queries, or management operations, reject any link without a `✓`, across database families, or otherwise unlisted. Product compatibility does not imply that this Skill supports the link.

<a id="directed-link-groups"></a>
## Registered synchronization links

### MySQL

| Source / destination | RDS MySQL | PolarDB MySQL | PolarDB-X 2.0 |
| --- | :---: | :---: | :---: |
| RDS MySQL | ✓ | ✓ | ✓ |
| PolarDB MySQL | ✓ | ✓ | ✓ |
| PolarDB-X 2.0 | ✓ | ✓ | ✓ |

### PostgreSQL

| Source / destination | RDS PostgreSQL | PolarDB PostgreSQL |
| --- | :---: | :---: |
| RDS PostgreSQL | ✓ | ✓ |
| PolarDB PostgreSQL | ✓ | ✓ |

When both sides are RDS PostgreSQL, the scenario is `rds-postgresql-to-rds-postgresql`. Resolve both instance names with `--type RDS --engine POSTGRESQL --page-size 20`; `--usage-type` is `src` on the source and `dest` on the destination. Do not use the PolarDB PostgreSQL flags (`POLARDB` / `POLARDB_PG`, page size 30) for an RDS PostgreSQL instance.

### MongoDB

| Source / destination | MongoDB replica set |
| --- | :---: |
| MongoDB replica set | ✓ |

Within one database family, both same-product and cross-product combinations are supported; combinations across database families are unsupported.

Use the product identifiers defined in the [source and destination database configuration](database-instance-configuration.md#database-instance-fields), and derive the Planner scenario as `<source-product-identifier>-to-<destination-product-identifier>`. Do not construct a scenario outside the matrices.

These links define only this Skill's management scope; they do not represent every synchronization scenario supported by the DTS service.
