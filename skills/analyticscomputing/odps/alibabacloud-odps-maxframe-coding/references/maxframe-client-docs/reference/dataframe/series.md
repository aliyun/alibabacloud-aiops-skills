# Series

## Constructor

| [`Series`](generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series)([data, index, dtype, name, copy, ...])   |    |
|-----------------------------------------------------------------------------------------------------------------------|----|

## Attributes

**Axes**

| [`Series.index`](generated/maxframe.dataframe.Series.index.md#maxframe.dataframe.Series.index)   | The index (axis labels) of the Series.   |
|--------------------------------------------------------------------------------------------------|------------------------------------------|

| [`Series.dtype`](generated/maxframe.dataframe.Series.dtype.md#maxframe.dataframe.Series.dtype)                                     | Return the dtype object of the underlying data.                   |
|------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`Series.memory_usage`](generated/maxframe.dataframe.Series.memory_usage.md#maxframe.dataframe.Series.memory_usage)([index, deep]) | Return the memory usage of the Series.                            |
| [`Series.ndim`](generated/maxframe.dataframe.Series.ndim.md#maxframe.dataframe.Series.ndim)                                        | Return an int representing the number of axes / array dimensions. |
| [`Series.name`](generated/maxframe.dataframe.Series.name.md#maxframe.dataframe.Series.name)                                        |                                                                   |
| [`Series.shape`](generated/maxframe.dataframe.Series.shape.md#maxframe.dataframe.Series.shape)                                     |                                                                   |
| [`Series.T`](generated/maxframe.dataframe.Series.T.md#maxframe.dataframe.Series.T)                                                 | Return the transpose, which is by definition self.                |

## Conversion

| [`Series.astype`](generated/maxframe.dataframe.Series.astype.md#maxframe.dataframe.Series.astype)(dtype[, copy, errors])                        | Cast a pandas object to a specified dtype `dtype`.                       |
|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`Series.convert_dtypes`](generated/maxframe.dataframe.Series.convert_dtypes.md#maxframe.dataframe.Series.convert_dtypes)([infer_objects, ...]) | Convert columns to best possible dtypes using dtypes supporting `pd.NA`. |
| [`Series.copy`](generated/maxframe.dataframe.Series.copy.md#maxframe.dataframe.Series.copy)([deep])                                             | Make a copy of this object's indices and data.                           |
| [`Series.infer_objects`](generated/maxframe.dataframe.Series.infer_objects.md#maxframe.dataframe.Series.infer_objects)([copy])                  | Attempt to infer better dtypes for object columns.                       |
| [`Series.to_frame`](generated/maxframe.dataframe.Series.to_frame.md#maxframe.dataframe.Series.to_frame)([name])                                 | Convert Series to DataFrame.                                             |

## Index, iteration

| [`Series.at`](generated/maxframe.dataframe.Series.at.md#maxframe.dataframe.Series.at)                                             | Access a single value for a row/column label pair.                 |
|-----------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`Series.iat`](generated/maxframe.dataframe.Series.iat.md#maxframe.dataframe.Series.iat)                                          | Access a single value for a row/column pair by integer position.   |
| [`Series.iloc`](generated/maxframe.dataframe.Series.iloc.md#maxframe.dataframe.Series.iloc)                                       | Purely integer-location based indexing for selection by position.  |
| [`Series.loc`](generated/maxframe.dataframe.Series.loc.md#maxframe.dataframe.Series.loc)                                          | Access a group of rows and columns by label(s) or a boolean array. |
| [`Series.mask`](generated/maxframe.dataframe.Series.mask.md#maxframe.dataframe.Series.mask)(cond[, other, inplace, axis, ...])    | Replace values where the condition is True.                        |
| [`Series.pop`](generated/maxframe.dataframe.Series.pop.md#maxframe.dataframe.Series.pop)(item)                                    | Return item and drops from series.                                 |
| [`Series.xs`](generated/maxframe.dataframe.Series.xs.md#maxframe.dataframe.Series.xs)(key[, axis, level, drop_level])             | Return cross-section from the Series/DataFrame.                    |
| [`Series.where`](generated/maxframe.dataframe.Series.where.md#maxframe.dataframe.Series.where)(cond[, other, inplace, axis, ...]) | Replace values where the condition is False.                       |

## Binary operator functions

| [`Series.add`](generated/maxframe.dataframe.Series.add.md#maxframe.dataframe.Series.add)(other[, level, fill_value, axis])                  | Return Addition of series and other, element-wise (binary operator add).                |
|---------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| [`Series.sub`](generated/maxframe.dataframe.Series.sub.md#maxframe.dataframe.Series.sub)(other[, level, fill_value, axis])                  | Return Subtraction of series and other, element-wise (binary operator subtract).        |
| [`Series.mul`](generated/maxframe.dataframe.Series.mul.md#maxframe.dataframe.Series.mul)(other[, level, fill_value, axis])                  | Return Multiplication of series and other, element-wise (binary operator mul).          |
| [`Series.div`](generated/maxframe.dataframe.Series.div.md#maxframe.dataframe.Series.div)(other[, level, fill_value, axis])                  | Return Floating division of series and other, element-wise (binary operator truediv).   |
| [`Series.truediv`](generated/maxframe.dataframe.Series.truediv.md#maxframe.dataframe.Series.truediv)(other[, level, fill_value, axis])      | Return Floating division of series and other, element-wise (binary operator truediv).   |
| [`Series.floordiv`](generated/maxframe.dataframe.Series.floordiv.md#maxframe.dataframe.Series.floordiv)(other[, level, fill_value, axis])   | Return Integer division of series and other, element-wise (binary operator floordiv).   |
| [`Series.mod`](generated/maxframe.dataframe.Series.mod.md#maxframe.dataframe.Series.mod)(other[, level, fill_value, axis])                  | Return Modulo of series and other, element-wise (binary operator mod).                  |
| [`Series.pow`](generated/maxframe.dataframe.Series.pow.md#maxframe.dataframe.Series.pow)(other[, level, fill_value, axis])                  | Return Exponential power of series and other, element-wise (binary operator pow).       |
| [`Series.radd`](generated/maxframe.dataframe.Series.radd.md#maxframe.dataframe.Series.radd)(other[, level, fill_value, axis])               | Return Addition of series and other, element-wise (binary operator radd).               |
| [`Series.rsub`](generated/maxframe.dataframe.Series.rsub.md#maxframe.dataframe.Series.rsub)(other[, level, fill_value, axis])               | Return Subtraction of series and other, element-wise (binary operator rsubtract).       |
| [`Series.rmul`](generated/maxframe.dataframe.Series.rmul.md#maxframe.dataframe.Series.rmul)(other[, level, fill_value, axis])               | Return Multiplication of series and other, element-wise (binary operator rmul).         |
| [`Series.rdiv`](generated/maxframe.dataframe.Series.rdiv.md#maxframe.dataframe.Series.rdiv)(other[, level, fill_value, axis])               | Return Floating division of series and other, element-wise (binary operator rtruediv).  |
| [`Series.rtruediv`](generated/maxframe.dataframe.Series.rtruediv.md#maxframe.dataframe.Series.rtruediv)(other[, level, fill_value, axis])   | Return Floating division of series and other, element-wise (binary operator rtruediv).  |
| [`Series.rfloordiv`](generated/maxframe.dataframe.Series.rfloordiv.md#maxframe.dataframe.Series.rfloordiv)(other[, level, fill_value, ...]) | Return Integer division of series and other, element-wise (binary operator rfloordiv).  |
| [`Series.rmod`](generated/maxframe.dataframe.Series.rmod.md#maxframe.dataframe.Series.rmod)(other[, level, fill_value, axis])               | Return Modulo of series and other, element-wise (binary operator rmod).                 |
| [`Series.rpow`](generated/maxframe.dataframe.Series.rpow.md#maxframe.dataframe.Series.rpow)(other[, level, fill_value, axis])               | Return Exponential power of series and other, element-wise (binary operator rpow).      |
| [`Series.lt`](generated/maxframe.dataframe.Series.lt.md#maxframe.dataframe.Series.lt)(other[, level, fill_value, axis])                     | Return Less than of series and other, element-wise (binary operator lt).                |
| [`Series.gt`](generated/maxframe.dataframe.Series.gt.md#maxframe.dataframe.Series.gt)(other[, level, fill_value, axis])                     | Return Greater than of series and other, element-wise (binary operator gt).             |
| [`Series.le`](generated/maxframe.dataframe.Series.le.md#maxframe.dataframe.Series.le)(other[, level, fill_value, axis])                     | Return Less than or equal to of series and other, element-wise (binary operator le).    |
| [`Series.ge`](generated/maxframe.dataframe.Series.ge.md#maxframe.dataframe.Series.ge)(other[, level, fill_value, axis])                     | Return Greater than or equal to of series and other, element-wise (binary operator ge). |
| [`Series.ne`](generated/maxframe.dataframe.Series.ne.md#maxframe.dataframe.Series.ne)(other[, level, fill_value, axis])                     | Return Not equal to of series and other, element-wise (binary operator ne).             |
| [`Series.eq`](generated/maxframe.dataframe.Series.eq.md#maxframe.dataframe.Series.eq)(other[, level, fill_value, axis])                     | Return Equal to of series and other, element-wise (binary operator eq).                 |
| [`Series.combine`](generated/maxframe.dataframe.Series.combine.md#maxframe.dataframe.Series.combine)(other, func[, fill_value])             | Combine the Series with a Series or scalar according to func.                           |
| [`Series.combine_first`](generated/maxframe.dataframe.Series.combine_first.md#maxframe.dataframe.Series.combine_first)(other)               | Update null elements with value in the same location in 'other'.                        |

## Function application, groupby & window

| [`Series.apply`](generated/maxframe.dataframe.Series.apply.md#maxframe.dataframe.Series.apply)(func[, convert_dtype, ...])             | Invoke function on values of Series.                            |
|----------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`Series.agg`](generated/maxframe.dataframe.Series.agg.md#maxframe.dataframe.Series.agg)([func, axis])                                 | Aggregate using one or more operations over the specified axis. |
| [`Series.aggregate`](generated/maxframe.dataframe.Series.aggregate.md#maxframe.dataframe.Series.aggregate)([func, axis])               | Aggregate using one or more operations over the specified axis. |
| [`Series.ewm`](generated/maxframe.dataframe.Series.ewm.md#maxframe.dataframe.Series.ewm)([com, span, halflife, alpha, ...])            | Provide exponential weighted functions.                         |
| [`Series.expanding`](generated/maxframe.dataframe.Series.expanding.md#maxframe.dataframe.Series.expanding)([min_periods, shift, ...])  | Provide expanding transformations.                              |
| [`Series.groupby`](generated/maxframe.dataframe.Series.groupby.md#maxframe.dataframe.Series.groupby)([by, level, as_index, sort, ...]) | Group DataFrame using a mapper or by a Series of columns.       |
| [`Series.map`](generated/maxframe.dataframe.Series.map.md#maxframe.dataframe.Series.map)(arg[, na_action, dtype, ...])                 | Map values of Series according to input correspondence.         |
| [`Series.rolling`](generated/maxframe.dataframe.Series.rolling.md#maxframe.dataframe.Series.rolling)(window[, min_periods, ...])       | Provide rolling window calculations.                            |
| [`Series.transform`](generated/maxframe.dataframe.Series.transform.md#maxframe.dataframe.Series.transform)(func[, convert_dtype, ...]) | Call `func` on self producing a Series with transformed values. |

<a id="generated-series-stats"></a>

## Computations / descriptive stats

| [`Series.abs`](generated/maxframe.dataframe.Series.abs.md#maxframe.dataframe.Series.abs)()                                                           |                                                                         |
|------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`Series.all`](generated/maxframe.dataframe.Series.all.md#maxframe.dataframe.Series.all)([axis, bool_only, skipna, level, ...])                      |                                                                         |
| [`Series.any`](generated/maxframe.dataframe.Series.any.md#maxframe.dataframe.Series.any)([axis, bool_only, skipna, level, ...])                      |                                                                         |
| [`Series.between`](generated/maxframe.dataframe.Series.between.md#maxframe.dataframe.Series.between)(left, right[, inclusive])                       | Return boolean Series equivalent to left <= series <= right.            |
| [`Series.clip`](generated/maxframe.dataframe.Series.clip.md#maxframe.dataframe.Series.clip)([lower, upper, axis, inplace])                           | Trim values at input threshold(s).                                      |
| [`Series.corr`](generated/maxframe.dataframe.Series.corr.md#maxframe.dataframe.Series.corr)(other[, method, min_periods])                            | Compute correlation with other Series, excluding missing values.        |
| [`Series.count`](generated/maxframe.dataframe.Series.count.md#maxframe.dataframe.Series.count)([level])                                              |                                                                         |
| [`Series.cov`](generated/maxframe.dataframe.Series.cov.md#maxframe.dataframe.Series.cov)(other[, min_periods, ddof])                                 | Compute covariance with Series, excluding missing values.               |
| [`Series.describe`](generated/maxframe.dataframe.Series.describe.md#maxframe.dataframe.Series.describe)([percentiles, include, exclude])             | Generate descriptive statistics.                                        |
| [`Series.factorize`](generated/maxframe.dataframe.Series.factorize.md#maxframe.dataframe.Series.factorize)([sort, use_na_sentinel])                  | Encode the object as an enumerated type or categorical variable.        |
| [`Series.is_monotonic_increasing`](generated/maxframe.dataframe.Series.is_monotonic_increasing.md#maxframe.dataframe.Series.is_monotonic_increasing) | Return boolean scalar if values in the object are monotonic_increasing. |
| [`Series.is_monotonic_decreasing`](generated/maxframe.dataframe.Series.is_monotonic_decreasing.md#maxframe.dataframe.Series.is_monotonic_decreasing) | Return boolean scalar if values in the object are monotonic_decreasing. |
| [`Series.is_unique`](generated/maxframe.dataframe.Series.is_unique.md#maxframe.dataframe.Series.is_unique)                                           | Return boolean if values in the object are unique.                      |
| [`Series.max`](generated/maxframe.dataframe.Series.max.md#maxframe.dataframe.Series.max)([axis, skipna, level, method])                              |                                                                         |
| [`Series.mean`](generated/maxframe.dataframe.Series.mean.md#maxframe.dataframe.Series.mean)([axis, skipna, level, method])                           |                                                                         |
| [`Series.median`](generated/maxframe.dataframe.Series.median.md#maxframe.dataframe.Series.median)([axis, skipna, level, method])                     |                                                                         |
| [`Series.min`](generated/maxframe.dataframe.Series.min.md#maxframe.dataframe.Series.min)([axis, skipna, level, method])                              |                                                                         |
| [`Series.mode`](generated/maxframe.dataframe.Series.mode.md#maxframe.dataframe.Series.mode)([dropna, combine_size])                                  | Return the mode(s) of the Series.                                       |
| [`Series.nlargest`](generated/maxframe.dataframe.Series.nlargest.md#maxframe.dataframe.Series.nlargest)(n[, keep])                                   | Return the largest n elements.                                          |
| [`Series.nsmallest`](generated/maxframe.dataframe.Series.nsmallest.md#maxframe.dataframe.Series.nsmallest)(n[, keep])                                | Return the smallest n elements.                                         |
| [`Series.nunique`](generated/maxframe.dataframe.Series.nunique.md#maxframe.dataframe.Series.nunique)([dropna])                                       | Return number of unique elements in the object.                         |
| [`Series.prod`](generated/maxframe.dataframe.Series.prod.md#maxframe.dataframe.Series.prod)([axis, skipna, level, ...])                              |                                                                         |
| [`Series.product`](generated/maxframe.dataframe.Series.product.md#maxframe.dataframe.Series.product)([axis, skipna, level, ...])                     |                                                                         |
| [`Series.quantile`](generated/maxframe.dataframe.Series.quantile.md#maxframe.dataframe.Series.quantile)([q, interpolation])                          | Return value at the given quantile.                                     |
| [`Series.rank`](generated/maxframe.dataframe.Series.rank.md#maxframe.dataframe.Series.rank)([axis, method, numeric_only, ...])                       | Compute numerical data ranks (1 through n) along axis.                  |
| [`Series.round`](generated/maxframe.dataframe.Series.round.md#maxframe.dataframe.Series.round)([decimals])                                           | Round each value in a Series to the given number of decimals.           |
| [`Series.sem`](generated/maxframe.dataframe.Series.sem.md#maxframe.dataframe.Series.sem)([axis, skipna, level, ddof, method])                        |                                                                         |
| [`Series.std`](generated/maxframe.dataframe.Series.std.md#maxframe.dataframe.Series.std)([axis, skipna, level, ddof, method])                        |                                                                         |
| [`Series.sum`](generated/maxframe.dataframe.Series.sum.md#maxframe.dataframe.Series.sum)([axis, skipna, level, min_count, ...])                      |                                                                         |
| [`Series.unique`](generated/maxframe.dataframe.Series.unique.md#maxframe.dataframe.Series.unique)([method])                                          | Uniques are returned in order of appearance.                            |
| [`Series.value_counts`](generated/maxframe.dataframe.Series.value_counts.md#maxframe.dataframe.Series.value_counts)([normalize, sort, ...])          | Return a Series containing counts of unique values.                     |
| [`Series.var`](generated/maxframe.dataframe.Series.var.md#maxframe.dataframe.Series.var)([axis, skipna, level, ddof, method])                        |                                                                         |

## Reindexing / selection / label manipulation

| [`Series.add_prefix`](generated/maxframe.dataframe.Series.add_prefix.md#maxframe.dataframe.Series.add_prefix)(prefix)                              | Prefix labels with string prefix.                                             |
|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`Series.add_suffix`](generated/maxframe.dataframe.Series.add_suffix.md#maxframe.dataframe.Series.add_suffix)(suffix)                              | Suffix labels with string suffix.                                             |
| [`Series.align`](generated/maxframe.dataframe.Series.align.md#maxframe.dataframe.Series.align)(other[, join, axis, level, ...])                    | Align two objects on their axes with the specified join method.               |
| [`Series.at_time`](generated/maxframe.dataframe.Series.at_time.md#maxframe.dataframe.Series.at_time)(time[, axis])                                 | Select values at particular time of day (e.g., 9:30AM).                       |
| [`Series.between_time`](generated/maxframe.dataframe.Series.between_time.md#maxframe.dataframe.Series.between_time)(start_time, end_time[, ...])   | Select values between particular times of the day (e.g., 9:00-9:30 AM).       |
| [`Series.case_when`](generated/maxframe.dataframe.Series.case_when.md#maxframe.dataframe.Series.case_when)(caselist)                               | Replace values where the conditions are True.                                 |
| [`Series.drop`](generated/maxframe.dataframe.Series.drop.md#maxframe.dataframe.Series.drop)([labels, axis, index, columns, ...])                   | Return Series with specified index labels removed.                            |
| [`Series.drop_duplicates`](generated/maxframe.dataframe.Series.drop_duplicates.md#maxframe.dataframe.Series.drop_duplicates)([keep, inplace, ...]) | Return Series with duplicate values removed.                                  |
| [`Series.droplevel`](generated/maxframe.dataframe.Series.droplevel.md#maxframe.dataframe.Series.droplevel)(level[, axis])                          | Return Series/DataFrame with requested index / column level(s) removed.       |
| [`Series.filter`](generated/maxframe.dataframe.Series.filter.md#maxframe.dataframe.Series.filter)([items, like, regex, axis])                      | Subset the dataframe rows or columns according to the specified index labels. |
| [`Series.head`](generated/maxframe.dataframe.Series.head.md#maxframe.dataframe.Series.head)([n])                                                   | Return the first n rows.                                                      |
| [`Series.idxmax`](generated/maxframe.dataframe.Series.idxmax.md#maxframe.dataframe.Series.idxmax)([axis, skipna])                                  | Return the row label of the maximum value.                                    |
| [`Series.idxmin`](generated/maxframe.dataframe.Series.idxmin.md#maxframe.dataframe.Series.idxmin)([axis, skipna])                                  | Return the row label of the minimum value.                                    |
| [`Series.isin`](generated/maxframe.dataframe.Series.isin.md#maxframe.dataframe.Series.isin)(values)                                                | Whether elements in Series are contained in values.                           |
| [`Series.reindex`](generated/maxframe.dataframe.Series.reindex.md#maxframe.dataframe.Series.reindex)([labels, index, columns, ...])                | Conform Series/DataFrame to new index with optional filling logic.            |
| [`Series.reindex_like`](generated/maxframe.dataframe.Series.reindex_like.md#maxframe.dataframe.Series.reindex_like)(other[, method, copy, ...])    | Return an object with matching indices as other object.                       |
| [`Series.rename`](generated/maxframe.dataframe.Series.rename.md#maxframe.dataframe.Series.rename)([index, axis, copy, inplace, ...])               | Alter Series index labels or name.                                            |
| [`Series.reset_index`](generated/maxframe.dataframe.Series.reset_index.md#maxframe.dataframe.Series.reset_index)([level, drop, name, ...])         | Generate a new DataFrame or Series with the index reset.                      |
| [`Series.sample`](generated/maxframe.dataframe.Series.sample.md#maxframe.dataframe.Series.sample)([n, frac, replace, weights, ...])                | Return a random sample of items from an axis of object.                       |
| [`Series.set_axis`](generated/maxframe.dataframe.Series.set_axis.md#maxframe.dataframe.Series.set_axis)(labels[, axis, inplace])                   | Assign desired index to given axis.                                           |
| [`Series.take`](generated/maxframe.dataframe.Series.take.md#maxframe.dataframe.Series.take)(indices[, axis])                                       | Return the elements in the given *positional* indices along an axis.          |
| [`Series.truncate`](generated/maxframe.dataframe.Series.truncate.md#maxframe.dataframe.Series.truncate)([before, after, axis, copy])               | Truncate a Series or DataFrame before and after some index value.             |

## Missing data handling

| [`Series.dropna`](generated/maxframe.dataframe.Series.dropna.md#maxframe.dataframe.Series.dropna)([axis, inplace, how, ignore_index])   | Return a new Series with missing values removed.   |
|-----------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| [`Series.fillna`](generated/maxframe.dataframe.Series.fillna.md#maxframe.dataframe.Series.fillna)([value, method, axis, ...])           | Fill NA/NaN values using the specified method.     |
| [`Series.isna`](generated/maxframe.dataframe.Series.isna.md#maxframe.dataframe.Series.isna)()                                           | Detect missing values.                             |
| [`Series.notna`](generated/maxframe.dataframe.Series.notna.md#maxframe.dataframe.Series.notna)()                                        | Detect existing (non-missing) values.              |
| [`Series.dropna`](generated/maxframe.dataframe.Series.dropna.md#maxframe.dataframe.Series.dropna)([axis, inplace, how, ignore_index])   | Return a new Series with missing values removed.   |
| [`Series.fillna`](generated/maxframe.dataframe.Series.fillna.md#maxframe.dataframe.Series.fillna)([value, method, axis, ...])           | Fill NA/NaN values using the specified method.     |

## Reshaping, sorting

| [`Series.argmax`](generated/maxframe.dataframe.Series.argmax.md#maxframe.dataframe.Series.argmax)([axis, skipna])                            | Return int position of the smallest value in the Series.                   |
|----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`Series.argmin`](generated/maxframe.dataframe.Series.argmin.md#maxframe.dataframe.Series.argmin)([axis, skipna])                            | Return int position of the smallest value in the Series.                   |
| [`Series.argsort`](generated/maxframe.dataframe.Series.argsort.md#maxframe.dataframe.Series.argsort)([axis, kind, order, stable])            | Return the integer indices that would sort the Series values.              |
| [`Series.explode`](generated/maxframe.dataframe.Series.explode.md#maxframe.dataframe.Series.explode)([ignore_index, ...])                    | Transform each element of a list-like to a row.                            |
| [`Series.reorder_levels`](generated/maxframe.dataframe.Series.reorder_levels.md#maxframe.dataframe.Series.reorder_levels)(order)             | Rearrange index levels using input order.                                  |
| [`Series.repeat`](generated/maxframe.dataframe.Series.repeat.md#maxframe.dataframe.Series.repeat)(repeats[, axis])                           | Repeat elements of a Series.                                               |
| [`Series.sort_values`](generated/maxframe.dataframe.Series.sort_values.md#maxframe.dataframe.Series.sort_values)([axis, ascending, ...])     | Sort by the values.                                                        |
| [`Series.sort_index`](generated/maxframe.dataframe.Series.sort_index.md#maxframe.dataframe.Series.sort_index)([axis, level, ascending, ...]) | Sort object by labels (along an axis).                                     |
| [`Series.swaplevel`](generated/maxframe.dataframe.Series.swaplevel.md#maxframe.dataframe.Series.swaplevel)([i, j])                           | Swap levels i and j in a `MultiIndex`.                                     |
| [`Series.unstack`](generated/maxframe.dataframe.Series.unstack.md#maxframe.dataframe.Series.unstack)([level, fill_value])                    | Unstack, also known as pivot, Series with MultiIndex to produce DataFrame. |

## Combining / comparing / joining / merging

| [`Series.append`](generated/maxframe.dataframe.Series.append.md#maxframe.dataframe.Series.append)(other[, ignore_index, ...])   | Append rows of other to the end of caller, returning a new object.   |
|---------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`Series.compare`](generated/maxframe.dataframe.Series.compare.md#maxframe.dataframe.Series.compare)(other[, align_axis, ...])  | Compare to another Series and show the differences.                  |
| [`Series.update`](generated/maxframe.dataframe.Series.update.md#maxframe.dataframe.Series.update)(other)                        | Modify Series in place using values from passed Series.              |

## Time Series-related

| [`Series.first_valid_index`](generated/maxframe.dataframe.Series.first_valid_index.md#maxframe.dataframe.Series.first_valid_index)()   | Return index for first non-NA value or None, if no non-NA value is found.   |
|----------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`Series.last_valid_index`](generated/maxframe.dataframe.Series.last_valid_index.md#maxframe.dataframe.Series.last_valid_index)()      | Return index for last non-NA value or None, if no non-NA value is found.    |
| [`Series.shift`](generated/maxframe.dataframe.Series.shift.md#maxframe.dataframe.Series.shift)([periods, freq, axis, fill_value])      | Shift index by desired number of periods with an optional time freq.        |
| [`Series.tshift`](generated/maxframe.dataframe.Series.tshift.md#maxframe.dataframe.Series.tshift)([periods, freq, axis])               | Shift the time index, using the index's frequency if available.             |

## Accessors

Pandas provides dtype-specific methods under various accessors.
These are separate namespaces within [`Series`](generated/maxframe.dataframe.Series.md#maxframe.dataframe.Series) that only apply
to specific data types.

| Data Type                   | Accessor                       |
|-----------------------------|--------------------------------|
| Datetime, Timedelta, Period | [dt](#generated-series-dt)     |
| String                      | [str](#generated-series-str)   |
| Dict                        | [dict](#generated-series-dict) |

<a id="generated-series-dt"></a>

### Datetimelike properties

`Series.dt` can be used to access the values of the series as
datetimelike and return several properties.
These can be accessed like `Series.dt.<property>`.

#### Datetime properties

| [`Series.dt.date`](generated/maxframe.dataframe.Series.dt.date.md#maxframe.dataframe.Series.dt.date)                                     | Returns numpy array of python [`datetime.date`](https://docs.python.org/3/library/datetime.html#datetime.date) objects.         |
|------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| [`Series.dt.time`](generated/maxframe.dataframe.Series.dt.time.md#maxframe.dataframe.Series.dt.time)                                     | Returns numpy array of [`datetime.time`](https://docs.python.org/3/library/datetime.html#datetime.time) objects.                |
| [`Series.dt.timetz`](generated/maxframe.dataframe.Series.dt.timetz.md#maxframe.dataframe.Series.dt.timetz)                               | Returns numpy array of [`datetime.time`](https://docs.python.org/3/library/datetime.html#datetime.time) objects with timezones. |
| [`Series.dt.year`](generated/maxframe.dataframe.Series.dt.year.md#maxframe.dataframe.Series.dt.year)                                     | The year of the datetime.                                                                                                       |
| [`Series.dt.month`](generated/maxframe.dataframe.Series.dt.month.md#maxframe.dataframe.Series.dt.month)                                  | The month as January=1, December=12.                                                                                            |
| [`Series.dt.day`](generated/maxframe.dataframe.Series.dt.day.md#maxframe.dataframe.Series.dt.day)                                        | The day of the datetime.                                                                                                        |
| [`Series.dt.hour`](generated/maxframe.dataframe.Series.dt.hour.md#maxframe.dataframe.Series.dt.hour)                                     | The hours of the datetime.                                                                                                      |
| [`Series.dt.minute`](generated/maxframe.dataframe.Series.dt.minute.md#maxframe.dataframe.Series.dt.minute)                               | The minutes of the datetime.                                                                                                    |
| [`Series.dt.second`](generated/maxframe.dataframe.Series.dt.second.md#maxframe.dataframe.Series.dt.second)                               | The seconds of the datetime.                                                                                                    |
| [`Series.dt.microsecond`](generated/maxframe.dataframe.Series.dt.microsecond.md#maxframe.dataframe.Series.dt.microsecond)                | The microseconds of the datetime.                                                                                               |
| [`Series.dt.nanosecond`](generated/maxframe.dataframe.Series.dt.nanosecond.md#maxframe.dataframe.Series.dt.nanosecond)                   | The nanoseconds of the datetime.                                                                                                |
| [`Series.dt.week`](generated/maxframe.dataframe.Series.dt.week.md#maxframe.dataframe.Series.dt.week)                                     | The week ordinal of the year.                                                                                                   |
| [`Series.dt.weekofyear`](generated/maxframe.dataframe.Series.dt.weekofyear.md#maxframe.dataframe.Series.dt.weekofyear)                   | The week ordinal of the year.                                                                                                   |
| [`Series.dt.dayofweek`](generated/maxframe.dataframe.Series.dt.dayofweek.md#maxframe.dataframe.Series.dt.dayofweek)                      | The day of the week with Monday=0, Sunday=6.                                                                                    |
| [`Series.dt.weekday`](generated/maxframe.dataframe.Series.dt.weekday.md#maxframe.dataframe.Series.dt.weekday)                            | The day of the week with Monday=0, Sunday=6.                                                                                    |
| [`Series.dt.dayofyear`](generated/maxframe.dataframe.Series.dt.dayofyear.md#maxframe.dataframe.Series.dt.dayofyear)                      | The ordinal day of the year.                                                                                                    |
| [`Series.dt.quarter`](generated/maxframe.dataframe.Series.dt.quarter.md#maxframe.dataframe.Series.dt.quarter)                            | The quarter of the date.                                                                                                        |
| [`Series.dt.is_month_start`](generated/maxframe.dataframe.Series.dt.is_month_start.md#maxframe.dataframe.Series.dt.is_month_start)       | Indicates whether the date is the first day of the month.                                                                       |
| [`Series.dt.is_month_end`](generated/maxframe.dataframe.Series.dt.is_month_end.md#maxframe.dataframe.Series.dt.is_month_end)             | Indicates whether the date is the last day of the month.                                                                        |
| [`Series.dt.is_quarter_start`](generated/maxframe.dataframe.Series.dt.is_quarter_start.md#maxframe.dataframe.Series.dt.is_quarter_start) | Indicator for whether the date is the first day of a quarter.                                                                   |
| [`Series.dt.is_quarter_end`](generated/maxframe.dataframe.Series.dt.is_quarter_end.md#maxframe.dataframe.Series.dt.is_quarter_end)       | Indicator for whether the date is the last day of a quarter.                                                                    |
| [`Series.dt.is_year_start`](generated/maxframe.dataframe.Series.dt.is_year_start.md#maxframe.dataframe.Series.dt.is_year_start)          | Indicate whether the date is the first day of a year.                                                                           |
| [`Series.dt.is_year_end`](generated/maxframe.dataframe.Series.dt.is_year_end.md#maxframe.dataframe.Series.dt.is_year_end)                | Indicate whether the date is the last day of the year.                                                                          |
| [`Series.dt.is_leap_year`](generated/maxframe.dataframe.Series.dt.is_leap_year.md#maxframe.dataframe.Series.dt.is_leap_year)             | Boolean indicator if the date belongs to a leap year.                                                                           |
| [`Series.dt.daysinmonth`](generated/maxframe.dataframe.Series.dt.daysinmonth.md#maxframe.dataframe.Series.dt.daysinmonth)                | The number of days in the month.                                                                                                |
| [`Series.dt.days_in_month`](generated/maxframe.dataframe.Series.dt.days_in_month.md#maxframe.dataframe.Series.dt.days_in_month)          | The number of days in the month.                                                                                                |

#### Datetime methods

| [`Series.dt.to_period`](generated/maxframe.dataframe.Series.dt.to_period.md#maxframe.dataframe.Series.dt.to_period)(\*args, \*\*kwargs)       | Cast to PeriodArray/PeriodIndex at a particular frequency.                                                                       |
|-----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| [`Series.dt.to_pydatetime`](generated/maxframe.dataframe.Series.dt.to_pydatetime.md#maxframe.dataframe.Series.dt.to_pydatetime)()             | Return the data as an array of [`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime.datetime) objects. |
| [`Series.dt.tz_localize`](generated/maxframe.dataframe.Series.dt.tz_localize.md#maxframe.dataframe.Series.dt.tz_localize)(\*args, \*\*kwargs) | Localize tz-naive Datetime Array/Index to tz-aware Datetime Array/Index.                                                         |
| [`Series.dt.tz_convert`](generated/maxframe.dataframe.Series.dt.tz_convert.md#maxframe.dataframe.Series.dt.tz_convert)(\*args, \*\*kwargs)    | Convert tz-aware Datetime Array/Index from one time zone to another.                                                             |
| [`Series.dt.normalize`](generated/maxframe.dataframe.Series.dt.normalize.md#maxframe.dataframe.Series.dt.normalize)(\*args, \*\*kwargs)       | Convert times to midnight.                                                                                                       |
| [`Series.dt.strftime`](generated/maxframe.dataframe.Series.dt.strftime.md#maxframe.dataframe.Series.dt.strftime)(\*args, \*\*kwargs)          | Convert to Index using specified date_format.                                                                                    |
| [`Series.dt.round`](generated/maxframe.dataframe.Series.dt.round.md#maxframe.dataframe.Series.dt.round)(\*args, \*\*kwargs)                   | Perform round operation on the data to the specified freq.                                                                       |
| [`Series.dt.floor`](generated/maxframe.dataframe.Series.dt.floor.md#maxframe.dataframe.Series.dt.floor)(\*args, \*\*kwargs)                   | Perform floor operation on the data to the specified freq.                                                                       |
| [`Series.dt.ceil`](generated/maxframe.dataframe.Series.dt.ceil.md#maxframe.dataframe.Series.dt.ceil)(\*args, \*\*kwargs)                      | Perform ceil operation on the data to the specified freq.                                                                        |
| [`Series.dt.month_name`](generated/maxframe.dataframe.Series.dt.month_name.md#maxframe.dataframe.Series.dt.month_name)(\*args, \*\*kwargs)    | Return the month names with specified locale.                                                                                    |
| [`Series.dt.day_name`](generated/maxframe.dataframe.Series.dt.day_name.md#maxframe.dataframe.Series.dt.day_name)(\*args, \*\*kwargs)          | Return the day names with specified locale.                                                                                      |

<a id="generated-series-str"></a>

### String handling

`Series.str` can be used to access the values of the series as
strings and apply several methods to it. These can be accessed like
`Series.str.<function/property>`.

| [`Series.str.capitalize`](generated/maxframe.dataframe.Series.str.capitalize.md#maxframe.dataframe.Series.str.capitalize)()                      | Convert strings in the Series/Index to be capitalized.                      |
|--------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`Series.str.contains`](generated/maxframe.dataframe.Series.str.contains.md#maxframe.dataframe.Series.str.contains)(pat[, case, flags, na, ...]) | Test if pattern or regex is contained within a string of a Series or Index. |
| [`Series.str.count`](generated/maxframe.dataframe.Series.str.count.md#maxframe.dataframe.Series.str.count)(pat[, flags])                         | Count occurrences of pattern in each string of the Series/Index.            |
| [`Series.str.endswith`](generated/maxframe.dataframe.Series.str.endswith.md#maxframe.dataframe.Series.str.endswith)(pat[, na])                   | Test if the end of each string element matches a pattern.                   |
| [`Series.str.find`](generated/maxframe.dataframe.Series.str.find.md#maxframe.dataframe.Series.str.find)(sub[, start, end])                       | Return lowest indexes in each strings in the Series/Index.                  |
| [`Series.str.len`](generated/maxframe.dataframe.Series.str.len.md#maxframe.dataframe.Series.str.len)()                                           | Compute the length of each element in the Series/Index.                     |
| [`Series.str.ljust`](generated/maxframe.dataframe.Series.str.ljust.md#maxframe.dataframe.Series.str.ljust)(width[, fillchar])                    | Pad right side of strings in the Series/Index.                              |
| [`Series.str.lower`](generated/maxframe.dataframe.Series.str.lower.md#maxframe.dataframe.Series.str.lower)()                                     | Convert strings in the Series/Index to lowercase.                           |
| [`Series.str.lstrip`](generated/maxframe.dataframe.Series.str.lstrip.md#maxframe.dataframe.Series.str.lstrip)([to_strip])                        | Remove leading characters.                                                  |
| [`Series.str.pad`](generated/maxframe.dataframe.Series.str.pad.md#maxframe.dataframe.Series.str.pad)(width[, side, fillchar])                    | Pad strings in the Series/Index up to width.                                |
| [`Series.str.repeat`](generated/maxframe.dataframe.Series.str.repeat.md#maxframe.dataframe.Series.str.repeat)(repeats)                           | Duplicate each string in the Series or Index.                               |
| [`Series.str.replace`](generated/maxframe.dataframe.Series.str.replace.md#maxframe.dataframe.Series.str.replace)(pat, repl[, n, case, ...])      | Replace each occurrence of pattern/regex in the Series/Index.               |
| [`Series.str.rfind`](generated/maxframe.dataframe.Series.str.rfind.md#maxframe.dataframe.Series.str.rfind)(sub[, start, end])                    | Return highest indexes in each strings in the Series/Index.                 |
| [`Series.str.rjust`](generated/maxframe.dataframe.Series.str.rjust.md#maxframe.dataframe.Series.str.rjust)(width[, fillchar])                    | Pad left side of strings in the Series/Index.                               |
| [`Series.str.rstrip`](generated/maxframe.dataframe.Series.str.rstrip.md#maxframe.dataframe.Series.str.rstrip)([to_strip])                        | Remove trailing characters.                                                 |
| [`Series.str.slice`](generated/maxframe.dataframe.Series.str.slice.md#maxframe.dataframe.Series.str.slice)([start, stop, step])                  | Slice substrings from each element in the Series or Index.                  |
| [`Series.str.startswith`](generated/maxframe.dataframe.Series.str.startswith.md#maxframe.dataframe.Series.str.startswith)(pat[, na])             | Test if the start of each string element matches a pattern.                 |
| [`Series.str.strip`](generated/maxframe.dataframe.Series.str.strip.md#maxframe.dataframe.Series.str.strip)([to_strip])                           | Remove leading and trailing characters.                                     |
| [`Series.str.swapcase`](generated/maxframe.dataframe.Series.str.swapcase.md#maxframe.dataframe.Series.str.swapcase)()                            | Convert strings in the Series/Index to be swapcased.                        |
| [`Series.str.title`](generated/maxframe.dataframe.Series.str.title.md#maxframe.dataframe.Series.str.title)()                                     | Convert strings in the Series/Index to titlecase.                           |
| [`Series.str.translate`](generated/maxframe.dataframe.Series.str.translate.md#maxframe.dataframe.Series.str.translate)(table)                    | Map all characters in the string through the given mapping table.           |
| [`Series.str.upper`](generated/maxframe.dataframe.Series.str.upper.md#maxframe.dataframe.Series.str.upper)()                                     | Convert strings in the Series/Index to uppercase.                           |
| [`Series.str.zfill`](generated/maxframe.dataframe.Series.str.zfill.md#maxframe.dataframe.Series.str.zfill)(width)                                | Pad strings in the Series/Index by prepending '0' characters.               |
| [`Series.str.isalnum`](generated/maxframe.dataframe.Series.str.isalnum.md#maxframe.dataframe.Series.str.isalnum)()                               | Check whether all characters in each string are alphanumeric.               |
| [`Series.str.isalpha`](generated/maxframe.dataframe.Series.str.isalpha.md#maxframe.dataframe.Series.str.isalpha)()                               | Check whether all characters in each string are alphabetic.                 |
| [`Series.str.isdigit`](generated/maxframe.dataframe.Series.str.isdigit.md#maxframe.dataframe.Series.str.isdigit)()                               | Check whether all characters in each string are digits.                     |
| [`Series.str.isspace`](generated/maxframe.dataframe.Series.str.isspace.md#maxframe.dataframe.Series.str.isspace)()                               | Check whether all characters in each string are whitespace.                 |
| [`Series.str.islower`](generated/maxframe.dataframe.Series.str.islower.md#maxframe.dataframe.Series.str.islower)()                               | Check whether all characters in each string are lowercase.                  |
| [`Series.str.isupper`](generated/maxframe.dataframe.Series.str.isupper.md#maxframe.dataframe.Series.str.isupper)()                               | Check whether all characters in each string are uppercase.                  |
| [`Series.str.istitle`](generated/maxframe.dataframe.Series.str.istitle.md#maxframe.dataframe.Series.str.istitle)()                               | Check whether all characters in each string are titlecase.                  |
| [`Series.str.isnumeric`](generated/maxframe.dataframe.Series.str.isnumeric.md#maxframe.dataframe.Series.str.isnumeric)()                         | Check whether all characters in each string are numeric.                    |
| [`Series.str.isdecimal`](generated/maxframe.dataframe.Series.str.isdecimal.md#maxframe.dataframe.Series.str.isdecimal)()                         | Check whether all characters in each string are decimal.                    |
<!-- The following is needed to ensure the generated pages are created with the
correct template (otherwise they would be created in the Series/Index class page) -->
<!-- .. autosummary::
   :toctree: generated/
   :template: accessor.rst

   Series.str
   Series.dt -->

<a id="generated-series-dict"></a>

### Dict properties

`Series.dict` can be used to access the methods of the series with dict values.
These can be accessed like `Series.dict.<method>`.

#### Dict methods

| [`Series.dict.__getitem__`](generated/maxframe.dataframe.Series.dict.__getitem__.md#maxframe.dataframe.Series.dict.__getitem__)(query_key)        | Get the value by the key of each dict in the Series.     |
|---------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`Series.dict.__setitem__`](generated/maxframe.dataframe.Series.dict.__setitem__.md#maxframe.dataframe.Series.dict.__setitem__)(query_key, value) | Set the value with the key to each dict of the Series.   |
| [`Series.dict.contains`](generated/maxframe.dataframe.Series.dict.contains.md#maxframe.dataframe.Series.dict.contains)(query_key)                 | Check whether the key is in each dict of the Series.     |
| [`Series.dict.get`](generated/maxframe.dataframe.Series.dict.get.md#maxframe.dataframe.Series.dict.get)(query_key[, default_value])               | Get the value by the key of each dict in the Series.     |
| [`Series.dict.len`](generated/maxframe.dataframe.Series.dict.len.md#maxframe.dataframe.Series.dict.len)()                                         | Get the length of each dict of the Series.               |
| [`Series.dict.remove`](generated/maxframe.dataframe.Series.dict.remove.md#maxframe.dataframe.Series.dict.remove)(query_key[, ignore_key_error])   | Remove the item by the key from each dict of the Series. |

<a id="generated-series-list"></a>

### List properties

`Series.list` can be used to access the methods of the series with list values.
These can be accessed like `Series.list.<method>`.

#### List methods

| [`Series.list.__getitem__`](generated/maxframe.dataframe.Series.list.__getitem__.md#maxframe.dataframe.Series.list.__getitem__)(query_index)   | Get the value by the index of each list in the Series.   |
|------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`Series.list.len`](generated/maxframe.dataframe.Series.list.len.md#maxframe.dataframe.Series.list.len)()                                      | Get the length of each list of the Series.               |

### Struct properties

`Series.struct` can be used to access the methods of the series with struct values.
These can be accessed like `Series.struct.<method>`.

#### Struct methods

| [`Series.struct.dtypes`](generated/maxframe.dataframe.Series.struct.dtypes.md#maxframe.dataframe.Series.struct.dtypes)             | Return the dtype object of each child field of the struct.   |
|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`Series.struct.field`](generated/maxframe.dataframe.Series.struct.field.md#maxframe.dataframe.Series.struct.field)(name_or_index) | Extract a child field of a struct as a Series.               |

## Plotting

`Series.plot` is both a callable method and a namespace attribute for
specific plotting methods of the form `Series.plot.<kind>`.

| [`Series.plot`](generated/maxframe.dataframe.Series.plot.md#maxframe.dataframe.Series.plot)   | alias of `SeriesPlotAccessor`   |
|-----------------------------------------------------------------------------------------------|---------------------------------|

| [`Series.plot.area`](generated/maxframe.dataframe.Series.plot.area.md#maxframe.dataframe.Series.plot.area)(\*args, \*\*kwargs)          | Draw a stacked area plot.                                     |
|-----------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`Series.plot.bar`](generated/maxframe.dataframe.Series.plot.bar.md#maxframe.dataframe.Series.plot.bar)(\*args, \*\*kwargs)             | Vertical bar plot.                                            |
| [`Series.plot.barh`](generated/maxframe.dataframe.Series.plot.barh.md#maxframe.dataframe.Series.plot.barh)(\*args, \*\*kwargs)          | Make a horizontal bar plot.                                   |
| [`Series.plot.box`](generated/maxframe.dataframe.Series.plot.box.md#maxframe.dataframe.Series.plot.box)(\*args, \*\*kwargs)             | Make a box plot of the DataFrame columns.                     |
| [`Series.plot.density`](generated/maxframe.dataframe.Series.plot.density.md#maxframe.dataframe.Series.plot.density)(\*args, \*\*kwargs) | Generate Kernel Density Estimate plot using Gaussian kernels. |
| [`Series.plot.hist`](generated/maxframe.dataframe.Series.plot.hist.md#maxframe.dataframe.Series.plot.hist)(\*args, \*\*kwargs)          | Draw one histogram of the DataFrame's columns.                |
| [`Series.plot.kde`](generated/maxframe.dataframe.Series.plot.kde.md#maxframe.dataframe.Series.plot.kde)(\*args, \*\*kwargs)             | Generate Kernel Density Estimate plot using Gaussian kernels. |
| [`Series.plot.line`](generated/maxframe.dataframe.Series.plot.line.md#maxframe.dataframe.Series.plot.line)(\*args, \*\*kwargs)          | Plot Series or DataFrame as lines.                            |
| [`Series.plot.pie`](generated/maxframe.dataframe.Series.plot.pie.md#maxframe.dataframe.Series.plot.pie)(\*args, \*\*kwargs)             | Generate a pie plot.                                          |

### Serialization / IO / conversion

| [`Series.to_csv`](generated/maxframe.dataframe.Series.to_csv.md#maxframe.dataframe.Series.to_csv)(path[, sep, na_rep, ...])            | Write object to a comma-separated values (csv) file.         |
|----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`Series.to_dict`](generated/maxframe.dataframe.Series.to_dict.md#maxframe.dataframe.Series.to_dict)([into, batch_size, session])      | Convert Series to {label -> value} dict or dict-like object. |
| [`Series.to_json`](generated/maxframe.dataframe.Series.to_json.md#maxframe.dataframe.Series.to_json)([path, orient, date_format, ...]) | Convert the object to a JSON string.                         |
| [`Series.to_list`](generated/maxframe.dataframe.Series.to_list.md#maxframe.dataframe.Series.to_list)([batch_size, session])            | Return a list of the values.                                 |

<a id="generated-series-mf"></a>

### MaxFrame Extensions

| [`Series.mf.apply_chunk`](generated/maxframe.dataframe.Series.mf.apply_chunk.md#maxframe.dataframe.Series.mf.apply_chunk)(func[, batch_rows, ...])   | Apply a function that takes pandas Series and outputs pandas DataFrame/Series.   |
|------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`Series.mf.flatmap`](generated/maxframe.dataframe.Series.mf.flatmap.md#maxframe.dataframe.Series.mf.flatmap)(func[, dtypes, dtype, ...])            | Apply the given function to each row and then flatten results.                   |
| [`Series.mf.flatjson`](generated/maxframe.dataframe.Series.mf.flatjson.md#maxframe.dataframe.Series.mf.flatjson)(query_paths[, dtypes, ...])         | Flat JSON object in the series to a dataframe according to JSON query.           |

`Series.mf` The Series.mf provides methods unique to MaxFrame. These methods are collated from application
scenarios in MaxCompute and these can be accessed like `Series.mf.<function/property>`.
