# Data input and output

## MaxCompute

### Read and convert to tables

Users can create MaxFrame DataFrame objects from MaxCompute tables with [`read_odps_table()`](../../reference/dataframe/generated/maxframe.dataframe.read_odps_table.md#maxframe.dataframe.read_odps_table)
, and store computed results into MaxCompute tables with [`DataFrame.to_odps_table()`](../../reference/dataframe/generated/maxframe.dataframe.DataFrame.to_odps_table.md#maxframe.dataframe.DataFrame.to_odps_table).

For instance, if you want to get data from non-partitioned table test_odps_table,
do some transformation by MaxFrame and store it into another partitioned table
test_processed_odps_table, you may use [`read_odps_table()`](../../reference/dataframe/generated/maxframe.dataframe.read_odps_table.md#maxframe.dataframe.read_odps_table) as is shown below.

```python
import maxframe.dataframe as md

df = md.read_odps_table("test_odps_table")
processed_df = df[df.A > 10]
processed_df.to_odps_table("test_processed_odps_table")
```

If the table is partitioned, `read_odps_table` will read data from all partitions which
should be definitely avoided if there are a number of partitions. You can select one
partition or a number of partitions with `partitions` argument.

```python
df = md.read_odps_table(
    "parted_odps_table", partitions=["pt1=20240119,pt2=10", "pt1=20240119,pt2=11"]
)
```

Values of partition columns are not included in results by default. If you need these values,
you may specify `append_partitions=True`.

```python
df = md.read_odps_table(
    "parted_odps_table", partitions=["pt1=20240119,pt2=10"], append_partitions=True
)
```

The resulting DataFrame will produce a RangeIndex by default. You may use `index_col`
argument to specify existing columns as indexes.

```python
df = md.read_odps_table(
    "parted_odps_table", partitions=["pt1=20240119,pt2=10"], index_col=["idx_col"]
)
```

If you want to store prepreocessed `df` into a MaxCompute table, you can use `to_odps_table()`
as is shown below.

```python
df.to_odps_table("output_table_name").execute()
```

You can control the behavior of index output via `index` and `index_label` arguments.
By default the index is outputted. If you do not want to output the index, you may specify
`index` argument as False.

```python
df.to_odps_table("output_table_name", index=False).execute()
```

The names of columns for indexes is the names of the indexes by default. If names of indexes
are not specified, the name `index` will be used if the index only has one level, or
`level_x` will be used, where `x` is the integer index of the level.

Data can be stored as partitioned tables. You may specify `partition` argument as the partition
to write.

```python
df.to_odps_table("parted_table", partition="pt=20240121,h=12").execute()
```

You can also specify columns as partition columns. The data of these columns will dynamically
decide the partition the row will be written to.

```python
df.to_odps_table("parted_table", partition_col=["pt_col"]).execute()
```

### Read from SQL queries

Users can create MaxFrame DataFrame objects with MaxCompute queries with [`read_odps_query()`](../../reference/dataframe/generated/maxframe.dataframe.read_odps_query.md#maxframe.dataframe.read_odps_query).
MaxFrame will retrieve DataFrame schema with [EXPLAIN](https://www.alibabacloud.com/help/zh/maxcompute/user-guide/explain) statement and execute
queries in MaxCompute.

For instance, you can create a DataFrame with SQL statement below.

```python
md_df = md.read_odps_query(
    "SELECT a.shop_name AS ashop, b.shop_name AS bshop FROM sale_detail_jt a "
    "RIGHT OUTER JOIN sale_detail b ON a.shop_name=b.shop_name"
)
```

## pandas objects

Users can convert between local pandas objects and DataFrames with [`read_pandas()`](../../reference/dataframe/generated/maxframe.dataframe.read_pandas.md#maxframe.dataframe.read_pandas)
and [`DataFrame.to_pandas()`](../../reference/dataframe/generated/maxframe.dataframe.DataFrame.to_pandas.md#maxframe.dataframe.DataFrame.to_pandas).

When `read_pandas` is called, these pandas objects will be uploaded to MaxCompute and
be used in the cluster.

```python
md_df = md.read_pandas(pd_df)
```

After transformation is done in MaxFrame, data can be downloaded to client with `to_pandas`.

```python
pd_df = md_df.to_pandas()
```
