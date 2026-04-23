# Index objects

## Constructor

| [`Index`](generated/maxframe.dataframe.Index.md#maxframe.dataframe.Index)(data, \*\*_)   |    |
|------------------------------------------------------------------------------------------|----|

## Properties

| [`Index.has_duplicates`](generated/maxframe.dataframe.Index.has_duplicates.md#maxframe.dataframe.Index.has_duplicates)                            |                                                                         |
|---------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`Index.hasnans`](generated/maxframe.dataframe.Index.hasnans.md#maxframe.dataframe.Index.hasnans)                                                 | Return True if there are any NaNs.                                      |
| [`Index.is_monotonic_decreasing`](generated/maxframe.dataframe.Index.is_monotonic_decreasing.md#maxframe.dataframe.Index.is_monotonic_decreasing) | Return boolean scalar if values in the object are monotonic_decreasing. |
| [`Index.is_monotonic_increasing`](generated/maxframe.dataframe.Index.is_monotonic_increasing.md#maxframe.dataframe.Index.is_monotonic_increasing) | Return boolean scalar if values in the object are monotonic_increasing. |
| [`Index.is_unique`](generated/maxframe.dataframe.Index.is_unique.md#maxframe.dataframe.Index.is_unique)                                           | Return boolean if values in the index are unique.                       |
| [`Index.name`](generated/maxframe.dataframe.Index.name.md#maxframe.dataframe.Index.name)                                                          |                                                                         |
| [`Index.names`](generated/maxframe.dataframe.Index.names.md#maxframe.dataframe.Index.names)                                                       |                                                                         |
| [`Index.ndim`](generated/maxframe.dataframe.Index.ndim.md#maxframe.dataframe.Index.ndim)                                                          |                                                                         |
| [`Index.size`](generated/maxframe.dataframe.Index.size.md#maxframe.dataframe.Index.size)                                                          |                                                                         |

## Modifying and computations

| [`Index.all`](generated/maxframe.dataframe.Index.all.md#maxframe.dataframe.Index.all)()                                                   |                                                                  |
|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`Index.any`](generated/maxframe.dataframe.Index.any.md#maxframe.dataframe.Index.any)()                                                   |                                                                  |
| [`Index.argmax`](generated/maxframe.dataframe.Index.argmax.md#maxframe.dataframe.Index.argmax)([axis, skipna])                            | Return int position of the smallest value in the Series.         |
| [`Index.argmin`](generated/maxframe.dataframe.Index.argmin.md#maxframe.dataframe.Index.argmin)([axis, skipna])                            | Return int position of the smallest value in the Series.         |
| [`Index.drop`](generated/maxframe.dataframe.Index.drop.md#maxframe.dataframe.Index.drop)(labels[, errors])                                | Make new Index with passed list of labels deleted.               |
| [`Index.drop_duplicates`](generated/maxframe.dataframe.Index.drop_duplicates.md#maxframe.dataframe.Index.drop_duplicates)([keep, method]) | Return Index with duplicate values removed.                      |
| [`Index.factorize`](generated/maxframe.dataframe.Index.factorize.md#maxframe.dataframe.Index.factorize)([sort, use_na_sentinel])          | Encode the object as an enumerated type or categorical variable. |
| [`Index.insert`](generated/maxframe.dataframe.Index.insert.md#maxframe.dataframe.Index.insert)(loc, value)                                | Make new Index inserting new item at location.                   |
| [`Index.max`](generated/maxframe.dataframe.Index.max.md#maxframe.dataframe.Index.max)([axis, skipna])                                     |                                                                  |
| [`Index.min`](generated/maxframe.dataframe.Index.min.md#maxframe.dataframe.Index.min)([axis, skipna])                                     |                                                                  |
| [`Index.rename`](generated/maxframe.dataframe.Index.rename.md#maxframe.dataframe.Index.rename)(name[, inplace])                           | Alter Index or MultiIndex name.                                  |
| [`Index.repeat`](generated/maxframe.dataframe.Index.repeat.md#maxframe.dataframe.Index.repeat)(repeats[, axis])                           | Repeat elements of an Index.                                     |

## Compatibility with MultiIndex

| [`Index.droplevel`](generated/maxframe.dataframe.Index.droplevel.md#maxframe.dataframe.Index.droplevel)(level)                   | Return index with requested level(s) removed.   |
|----------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|
| [`Index.set_names`](generated/maxframe.dataframe.Index.set_names.md#maxframe.dataframe.Index.set_names)(names[, level, inplace]) | Set Index or MultiIndex name.                   |

## Missing values

| [`Index.dropna`](generated/maxframe.dataframe.Index.dropna.md#maxframe.dataframe.Index.dropna)([how])             | Return Index without NA/NaN values.          |
|-------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| [`Index.fillna`](generated/maxframe.dataframe.Index.fillna.md#maxframe.dataframe.Index.fillna)([value, downcast]) | Fill NA/NaN values with the specified value. |
| [`Index.isna`](generated/maxframe.dataframe.Index.isna.md#maxframe.dataframe.Index.isna)()                        | Detect missing values.                       |
| [`Index.notna`](generated/maxframe.dataframe.Index.notna.md#maxframe.dataframe.Index.notna)()                     | Detect existing (non-missing) values.        |

## Conversion

| [`Index.astype`](generated/maxframe.dataframe.Index.astype.md#maxframe.dataframe.Index.astype)(dtype[, copy])          | Create an Index with values cast to dtypes.                         |
|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`Index.to_frame`](generated/maxframe.dataframe.Index.to_frame.md#maxframe.dataframe.Index.to_frame)([index, name])    | Create a DataFrame with a column containing the Index.              |
| [`Index.to_series`](generated/maxframe.dataframe.Index.to_series.md#maxframe.dataframe.Index.to_series)([index, name]) | Create a Series with both index and values equal to the index keys. |

## Sorting

| [`Index.argsort`](generated/maxframe.dataframe.Index.argsort.md#maxframe.dataframe.Index.argsort)(\*args, \*\*kwargs)   |    |
|-------------------------------------------------------------------------------------------------------------------------|----|

## Selecting

| [`Index.get_level_values`](generated/maxframe.dataframe.Index.get_level_values.md#maxframe.dataframe.Index.get_level_values)(level)   | Return vector of label values for requested level.   |
|---------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
