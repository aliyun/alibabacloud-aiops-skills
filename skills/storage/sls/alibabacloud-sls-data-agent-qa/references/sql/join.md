# Cross-Logstore JOIN

Use JOIN when answering a question requires correlating records across Logstores for verification or calculation. If only per-source statistics or comparisons are needed, query each source separately and then summarize the results.

- Use previously resolved query locations. All Logstores must belong to the same Region and Project.
- Verify the business meaning of join keys and the relationship between records using field definitions or actual data. Matching field names alone do not establish a valid join.
- Refer to the current Logstore as `log` and enclose other Logstore names in double quotes.
- For index-based SQL analysis, every field used in joins, filters, projections, or calculations must have analytics enabled in its table's index. Check the corresponding Logstore index when capabilities are unclear.
- In SCAN mode, qualify fields in cross-Logstore JOINs with `LogstoreName.key`.

Example using index-based SQL analysis:

```sql
<search-prefix> | SELECT a.<left_field>, b.<right_field>
FROM log a
JOIN "<other_logstore>" b ON a.<left_key> = b.<right_key>
```
