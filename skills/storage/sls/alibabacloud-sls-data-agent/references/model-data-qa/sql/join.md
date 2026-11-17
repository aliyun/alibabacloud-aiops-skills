# Cross-Logstore JOIN

Use JOIN when a question requires linking records from multiple Logstores for verification or calculation. When only separate-source statistics or comparisons are needed, query each source separately and summarize the results.

- Use execution coordinates already obtained. All Logstores must belong to the same Region and Project.
- Confirm the business meaning of join keys and the correspondence between records from field definitions or actual data. Matching field names alone do not establish a join relationship.
- Use `log` for the current Logstore and double-quoted names for other Logstores.
- In index analysis, fields used for joins, filters, projections, or calculations in SQL must have statistical analysis enabled in each table. Verify the relevant Logstore's index when capabilities are unclear.
- In SCAN mode, qualify cross-Logstore JOIN fields as `LogstoreName.key`.

Index analysis example:

```sql
<search-prefix> | SELECT a.<left_field>, b.<right_field>
FROM log a
JOIN "<other_logstore>" b ON a.<left_key> = b.<right_key>
```
