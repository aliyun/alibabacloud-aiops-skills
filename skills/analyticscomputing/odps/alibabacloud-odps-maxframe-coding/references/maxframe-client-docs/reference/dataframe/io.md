<a id="generated-io"></a>

# Input/output

## Clipboard

| [`read_clipboard`](generated/maxframe.dataframe.read_clipboard.md#maxframe.dataframe.read_clipboard)([sep])                                         | Read text from clipboard and pass to [`read_csv()`](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html#pandas.read_csv).   |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| [`DataFrame.to_clipboard`](generated/maxframe.dataframe.DataFrame.to_clipboard.md#maxframe.dataframe.DataFrame.to_clipboard)(\*[, excel, sep, ...]) | Copy object to the system clipboard.                                                                                                      |

## Flat file

| [`read_csv`](generated/maxframe.dataframe.read_csv.md#maxframe.dataframe.read_csv)(path, \*[, names, sep, index_col, ...])           | Read a comma-separated values (csv) file into DataFrame.   |
|--------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`DataFrame.to_csv`](generated/maxframe.dataframe.DataFrame.to_csv.md#maxframe.dataframe.DataFrame.to_csv)(path[, sep, na_rep, ...]) | Write object to a comma-separated values (csv) file.       |

## JSON

| [`read_json`](generated/maxframe.dataframe.read_json.md#maxframe.dataframe.read_json)(path, \*[, orient, typ, dtype, ...])         | Read a JSON file into a DataFrame.   |
|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| [`DataFrame.to_json`](generated/maxframe.dataframe.DataFrame.to_json.md#maxframe.dataframe.DataFrame.to_json)([path, orient, ...]) | Convert the object to a JSON string. |

## MaxCompute

| [`read_odps_query`](generated/maxframe.dataframe.read_odps_query.md#maxframe.dataframe.read_odps_query)(query[, odps_entry, ...])                        | Read data from a MaxCompute (ODPS) query into DataFrame.   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`read_odps_table`](generated/maxframe.dataframe.read_odps_table.md#maxframe.dataframe.read_odps_table)(table_name[, partitions, ...])                   | Read data from a MaxCompute (ODPS) table into DataFrame.   |
| [`DataFrame.to_odps_table`](generated/maxframe.dataframe.DataFrame.to_odps_table.md#maxframe.dataframe.DataFrame.to_odps_table)(table[, partition, ...]) | Write DataFrame object into a MaxCompute (ODPS) table.     |

## Native pandas

| [`read_pandas`](generated/maxframe.dataframe.read_pandas.md#maxframe.dataframe.read_pandas)(data, \*\*kwargs)                  | Create MaxFrame objects from pandas.   |
|--------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| [`DataFrame.to_pandas`](generated/maxframe.dataframe.DataFrame.to_pandas.md#maxframe.dataframe.DataFrame.to_pandas)([session]) |                                        |

## Parquet

| [`read_parquet`](generated/maxframe.dataframe.read_parquet.md#maxframe.dataframe.read_parquet)(path[, engine, columns, ...])                | Load a parquet object from the file path, returning a DataFrame.                              |
|---------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [`DataFrame.to_parquet`](generated/maxframe.dataframe.DataFrame.to_parquet.md#maxframe.dataframe.DataFrame.to_parquet)(path[, engine, ...]) | Write a DataFrame to the binary parquet format, each chunk will be written to a Parquet file. |
