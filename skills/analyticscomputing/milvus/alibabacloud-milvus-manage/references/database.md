# Database Management

```python
# Create a database
client.create_database(db_name="my_database")

# List all databases
databases = client.list_databases()
# Returns: ["default", "my_database"]

# Switch to a database
client.using_database(db_name="my_database")

# Drop a database (must drop all collections first)
client.drop_database(db_name="my_database")

# Or connect to a specific database at init (use the user's actual URI and credentials)
client = MilvusClient(uri="<USER_URI>", token="<USER_TOKEN>", db_name="my_database")
```

## Guidance

- Every Milvus instance has a `"default"` database.
- Before dropping a database, all collections in it must be dropped first.
