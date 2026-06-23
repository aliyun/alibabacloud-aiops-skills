## Description: <br>
Alibabacloud AnalyticDB PostgreSQL Query Skill — Enables any AI Agent to connect to AnalyticDB PostgreSQL (PostgreSQL-compatible) via psql, execute read-only queries, and optionally export results as local CSV files for further analysis. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
ghy <br>

### License/Terms of Use: <br>
MIT-0 <br>

## Use Case: <br>
Data analysts, business users, and developers describe their data needs in natural language. The Agent queries a DBA-configured Semantic Model (`_agent_meta` schema) to understand available tables, columns, and relationships, then generates SQL strictly within the model's scope. Results can be returned directly or exported as local CSV files for downstream analysis with tools like pandas. Applicable to data extraction, ad-hoc reporting, exploratory analysis, and cross-table joins. <br>

### Compatible Agents: <br>
Claude (Anthropic), ClawHub Skills, Qoder Worker, and any AI Agent with shell execution capability. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Database credentials may be leaked in conversation or logs. <br>
Mitigation: Credentials are passed via environment variables (PGPASSWORD). The Skill explicitly prohibits the Agent from echoing, printing, or hardcoding passwords. <br>
Risk: The Agent may execute write operations that corrupt data. <br>
Mitigation: Enforces read-only connections (default_transaction_read_only=on) at the database level, rejecting any write operations. A dedicated read-only database account is recommended as an additional safeguard. <br>
Risk: The Agent may access tables or columns beyond the intended scope. <br>
Mitigation: A Semantic Model (`_agent_meta` schema) acts as a hard gate — the Agent cannot execute any data query until the semantic model exists and passes a pre-query gate check. The Agent can only query tables, columns, and joins explicitly defined in the model. An anti-bypass clause explicitly prohibits rationalizing gate bypass (e.g., "user needs it urgently", "just this once"). Requests outside scope are refused with a message directing the user to contact the DBA. <br>
Risk: Exporting large result sets may exhaust disk space or slow down the database. <br>
Mitigation: Default LIMIT of 50,000 rows; large exports require confirmation of data volume before execution. <br>

## Reference(s): <br>
- [SKILL.md](artifact/SKILL.md) <br>
- [Connection Guide](artifact/references/connection-guide.md) <br>
- [SQL Guide](artifact/references/sql-guide.md) <br>
- [Export Guide](artifact/references/export-guide.md) <br>
- [Semantic Model Guide](artifact/references/semantic-model-guide.md) <br>
- [Resource Group Guide](artifact/references/resource-group-guide.md) <br>

## Skill Output: <br>
**Output Type(s):** [SQL, CSV files, Shell commands, Text] <br>
**Output Format:** [Markdown with inline SQL and CSV file exports] <br>
**Output Parameters:** [1D] <br>

## Skill Version(s): <br>
0.0.1 <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their data security environment. Agent-generated SQL should be reviewed and confirmed before execution. Exported data must comply with the organization's data classification and masking requirements. <br>
