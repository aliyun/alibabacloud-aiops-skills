# Introduction

The SAP HANA data source provides you with bidirectional read and write capabilities for SAP HANA. This article introduces the data synchronization capabilities of DataWorks for SAP HANA.

# Source

## Parameter Description

| Parameter | Description | Required | Default Value | Supported in Wizard Mode | Remarks |
|----------|----------|----------|--------|------------------|------|
| username | Username. | N | None | Y |  |
| password | Password. | N | None | Y |  |
| column | The names of the fields to be synced. Use an asterisk (\*) to sync all columns. **Note** When a field name in SAP HANA Reader contains a slash (/), you need to escape it using backslash plus double quotes (\\"your_column_name\\"), for example, if the field name is /abc/efg, the escaped field name is \\"/abc/efg\\". | N | None | Y |  |
| table | The name of the table to be synced. | N | None | Y |  |
| jdbcUrl | The JDBC URL for connecting to HANA. For example, jdbc:sap://127.0.0.1:30215?currentschema=TEST. | N | None | Y |  |
| splitPk | A field in the HANA table used as the split field for synchronization. The split field helps with multi-concurrency synchronization of HANA tables. The split field must be an integer numeric field. If there is no such field type, it can be left blank. | N | None | Y |  |

> Y = Yes, N = No

## Configuration Example

```json
{
  "stepType": "saphana",
  "parameter": {
    "username": "",
    "password": "",
    "column": [],
    "table": "",
    "jdbcUrl": "",
    "splitPk": ""
  },
  "name": "Reader",
  "category": "reader"
}
```
