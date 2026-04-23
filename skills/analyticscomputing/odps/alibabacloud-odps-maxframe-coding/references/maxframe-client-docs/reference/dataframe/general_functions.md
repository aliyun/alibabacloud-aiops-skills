<a id="generated-general-functions"></a>

# General functions

## Data manipulations

| [`concat`](generated/maxframe.dataframe.concat.md#maxframe.dataframe.concat)(objs[, axis, join, ignore_index, ...])          | Concatenate dataframe objects along a particular axis with optional set logic along the other axes.   |
|------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| [`factorize`](generated/maxframe.dataframe.factorize.md#maxframe.dataframe.factorize)(values[, sort, use_na_sentinel])       | Encode the object as an enumerated type or categorical variable.                                      |
| [`get_dummies`](generated/maxframe.dataframe.get_dummies.md#maxframe.dataframe.get_dummies)(data[, prefix, prefix_sep, ...]) | Convert categorical variable into dummy/indicator variables.                                          |
| [`merge`](generated/maxframe.dataframe.merge.md#maxframe.dataframe.merge)(df, right[, how, on, left_on, ...])                | Merge DataFrame or named Series objects with a database-style join.                                   |

## Top-level missing data

| [`isna`](generated/maxframe.dataframe.isna.md#maxframe.dataframe.isna)(obj)          | Detect missing values.                |
|--------------------------------------------------------------------------------------|---------------------------------------|
| [`isnull`](generated/maxframe.dataframe.isnull.md#maxframe.dataframe.isnull)(obj)    | Detect missing values.                |
| [`notna`](generated/maxframe.dataframe.notna.md#maxframe.dataframe.notna)(obj)       | Detect existing (non-missing) values. |
| [`notnull`](generated/maxframe.dataframe.notnull.md#maxframe.dataframe.notnull)(obj) | Detect existing (non-missing) values. |

### Top-level dealing with numeric data

| [`to_numeric`](generated/maxframe.dataframe.to_numeric.md#maxframe.dataframe.to_numeric)(arg[, errors, downcast])   | Convert argument to a numeric type.   |
|---------------------------------------------------------------------------------------------------------------------|---------------------------------------|

## Top-level dealing with datetimelike

| [`to_datetime`](generated/maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)(arg[, errors, dayfirst, ...])      | Convert argument to datetime.           |
|--------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| [`date_range`](generated/maxframe.dataframe.date_range.md#maxframe.dataframe.date_range)([start, end, periods, freq, tz, ...]) | Return a fixed frequency DatetimeIndex. |

## Top-level evaluation

| [`eval`](generated/maxframe.dataframe.eval.md#maxframe.dataframe.eval)(expr[, parser, engine, local_dict, ...])   | Evaluate a Python expression as a string using various backends.   |
|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
