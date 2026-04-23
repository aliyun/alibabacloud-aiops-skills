# maxframe.dataframe.Index

### *class* maxframe.dataframe.Index(data, \*\*\_)

#### \_\_init_\_(data=None, dtype=None, copy=False, name=None, tupleize_cols=True, chunk_size=None, gpu=None, sparse=None, names=None, num_partitions=None, store_data=False)

### Methods

| [`__init__`](#maxframe.dataframe.Index.__init__)([data, dtype, copy, name, ...])                                          |                                                                       |
|---------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `agg`([func, axis])                                                                                                       | Aggregate using one or more operations over the specified axis.       |
| `aggregate`([func, axis])                                                                                                 | Aggregate using one or more operations over the specified axis.       |
| [`all`](maxframe.dataframe.Index.all.md#maxframe.dataframe.Index.all)()                                                   |                                                                       |
| [`any`](maxframe.dataframe.Index.any.md#maxframe.dataframe.Index.any)()                                                   |                                                                       |
| [`argmax`](maxframe.dataframe.Index.argmax.md#maxframe.dataframe.Index.argmax)([axis, skipna])                            | Return int position of the smallest value in the Series.              |
| [`argmin`](maxframe.dataframe.Index.argmin.md#maxframe.dataframe.Index.argmin)([axis, skipna])                            | Return int position of the smallest value in the Series.              |
| [`argsort`](maxframe.dataframe.Index.argsort.md#maxframe.dataframe.Index.argsort)(\*args, \*\*kwargs)                     |                                                                       |
| [`astype`](maxframe.dataframe.Index.astype.md#maxframe.dataframe.Index.astype)(dtype[, copy])                             | Create an Index with values cast to dtypes.                           |
| `check_monotonic`([decreasing, strict])                                                                                   | Check if values in the object are monotonic increasing or decreasing. |
| `clip`([lower, upper, axis, inplace])                                                                                     | Trim values at input threshold(s).                                    |
| `copy`()                                                                                                                  |                                                                       |
| `copy_from`(obj)                                                                                                          |                                                                       |
| `copy_to`(target)                                                                                                         |                                                                       |
| [`drop`](maxframe.dataframe.Index.drop.md#maxframe.dataframe.Index.drop)(labels[, errors])                                | Make new Index with passed list of labels deleted.                    |
| [`drop_duplicates`](maxframe.dataframe.Index.drop_duplicates.md#maxframe.dataframe.Index.drop_duplicates)([keep, method]) | Return Index with duplicate values removed.                           |
| [`droplevel`](maxframe.dataframe.Index.droplevel.md#maxframe.dataframe.Index.droplevel)(level)                            | Return index with requested level(s) removed.                         |
| [`dropna`](maxframe.dataframe.Index.dropna.md#maxframe.dataframe.Index.dropna)([how])                                     | Return Index without NA/NaN values.                                   |
| `duplicated`([keep])                                                                                                      | Indicate duplicate index values.                                      |
| `execute`([session])                                                                                                      |                                                                       |
| [`factorize`](maxframe.dataframe.Index.factorize.md#maxframe.dataframe.Index.factorize)([sort, use_na_sentinel])          | Encode the object as an enumerated type or categorical variable.      |
| [`fillna`](maxframe.dataframe.Index.fillna.md#maxframe.dataframe.Index.fillna)([value, downcast])                         | Fill NA/NaN values with the specified value.                          |
| [`get_level_values`](maxframe.dataframe.Index.get_level_values.md#maxframe.dataframe.Index.get_level_values)(level)       | Return vector of label values for requested level.                    |
| [`insert`](maxframe.dataframe.Index.insert.md#maxframe.dataframe.Index.insert)(loc, value)                                | Make new Index inserting new item at location.                        |
| [`isna`](maxframe.dataframe.Index.isna.md#maxframe.dataframe.Index.isna)()                                                | Detect missing values.                                                |
| `isnull`()                                                                                                                | Detect missing values.                                                |
| `map`(mapper[, na_action, dtype, ...])                                                                                    | Map values using input correspondence (a dict, Series, or function).  |
| [`max`](maxframe.dataframe.Index.max.md#maxframe.dataframe.Index.max)([axis, skipna])                                     |                                                                       |
| `memory_usage`([deep])                                                                                                    | Memory usage of the values.                                           |
| [`min`](maxframe.dataframe.Index.min.md#maxframe.dataframe.Index.min)([axis, skipna])                                     |                                                                       |
| [`notna`](maxframe.dataframe.Index.notna.md#maxframe.dataframe.Index.notna)()                                             | Detect existing (non-missing) values.                                 |
| `notnull`()                                                                                                               | Detect existing (non-missing) values.                                 |
| `rechunk`(chunk_size[, reassign_worker])                                                                                  |                                                                       |
| [`rename`](maxframe.dataframe.Index.rename.md#maxframe.dataframe.Index.rename)(name[, inplace])                           | Alter Index or MultiIndex name.                                       |
| [`repeat`](maxframe.dataframe.Index.repeat.md#maxframe.dataframe.Index.repeat)(repeats[, axis])                           | Repeat elements of an Index.                                          |
| [`set_names`](maxframe.dataframe.Index.set_names.md#maxframe.dataframe.Index.set_names)(names[, level, inplace])          | Set Index or MultiIndex name.                                         |
| [`to_frame`](maxframe.dataframe.Index.to_frame.md#maxframe.dataframe.Index.to_frame)([index, name])                       | Create a DataFrame with a column containing the Index.                |
| `to_pandas`([session])                                                                                                    |                                                                       |
| [`to_series`](maxframe.dataframe.Index.to_series.md#maxframe.dataframe.Index.to_series)([index, name])                    | Create a Series with both index and values equal to the index keys.   |
| `value_counts`([normalize, sort, ascending, ...])                                                                         | Return a Series containing counts of unique values.                   |

### Attributes

| `T`                                                                                                                               | Return the transpose, which is by definition self.                      |
|-----------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| `data`                                                                                                                            |                                                                         |
| [`has_duplicates`](maxframe.dataframe.Index.has_duplicates.md#maxframe.dataframe.Index.has_duplicates)                            |                                                                         |
| [`hasnans`](maxframe.dataframe.Index.hasnans.md#maxframe.dataframe.Index.hasnans)                                                 | Return True if there are any NaNs.                                      |
| `is_monotonic`                                                                                                                    | Return boolean scalar if values in the object are monotonic_increasing. |
| [`is_monotonic_decreasing`](maxframe.dataframe.Index.is_monotonic_decreasing.md#maxframe.dataframe.Index.is_monotonic_decreasing) | Return boolean scalar if values in the object are monotonic_decreasing. |
| [`is_monotonic_increasing`](maxframe.dataframe.Index.is_monotonic_increasing.md#maxframe.dataframe.Index.is_monotonic_increasing) | Return boolean scalar if values in the object are monotonic_increasing. |
| [`is_unique`](maxframe.dataframe.Index.is_unique.md#maxframe.dataframe.Index.is_unique)                                           | Return boolean if values in the index are unique.                       |
| [`name`](maxframe.dataframe.Index.name.md#maxframe.dataframe.Index.name)                                                          |                                                                         |
| [`names`](maxframe.dataframe.Index.names.md#maxframe.dataframe.Index.names)                                                       |                                                                         |
| [`ndim`](maxframe.dataframe.Index.ndim.md#maxframe.dataframe.Index.ndim)                                                          |                                                                         |
| `shape`                                                                                                                           |                                                                         |
| [`size`](maxframe.dataframe.Index.size.md#maxframe.dataframe.Index.size)                                                          |                                                                         |
| `type_name`                                                                                                                       |                                                                         |
| `values`                                                                                                                          |                                                                         |
