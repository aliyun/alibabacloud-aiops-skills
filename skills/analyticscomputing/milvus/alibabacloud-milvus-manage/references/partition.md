# Partition Management

```python
# Create a partition
client.create_partition(collection_name="my_collection", partition_name="partition_A")

# List partitions
partitions = client.list_partitions(collection_name="my_collection")
# Returns: ["_default", "partition_A"]

# Check if partition exists
exists = client.has_partition(collection_name="my_collection", partition_name="partition_A")

# Load specific partitions
client.load_partitions(collection_name="my_collection", partition_names=["partition_A"])

# Release specific partitions
client.release_partitions(collection_name="my_collection", partition_names=["partition_A"])

# Drop a partition
client.drop_partition(collection_name="my_collection", partition_name="partition_A")
```

## Guidance

- Every collection has a `_default` partition.
- Use `is_partition_key=True` on a field to enable automatic partitioning by field value.
- A partition must be loaded before search.
- Before dropping a partition, confirm with the user — all data in it will be deleted.
