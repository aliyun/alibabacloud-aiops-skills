<a id="generated-dataframe"></a>

# DataFrame

## Constructor

| [`DataFrame`](generated/maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)([data, index, columns, dtype, ...])   |    |
|-----------------------------------------------------------------------------------------------------------------------------|----|

## Attributes and underlying data

**Axes**

| [`DataFrame.index`](generated/maxframe.dataframe.DataFrame.index.md#maxframe.dataframe.DataFrame.index)       |    |
|---------------------------------------------------------------------------------------------------------------|----|
| [`DataFrame.columns`](generated/maxframe.dataframe.DataFrame.columns.md#maxframe.dataframe.DataFrame.columns) |    |

| [`DataFrame.dtypes`](generated/maxframe.dataframe.DataFrame.dtypes.md#maxframe.dataframe.DataFrame.dtypes)                                          | Return the dtypes in the DataFrame.                                    |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`DataFrame.memory_usage`](generated/maxframe.dataframe.DataFrame.memory_usage.md#maxframe.dataframe.DataFrame.memory_usage)([index, deep])         | Return the memory usage of each column in bytes.                       |
| [`DataFrame.ndim`](generated/maxframe.dataframe.DataFrame.ndim.md#maxframe.dataframe.DataFrame.ndim)                                                | Return an int representing the number of axes / array dimensions.      |
| [`DataFrame.select_dtypes`](generated/maxframe.dataframe.DataFrame.select_dtypes.md#maxframe.dataframe.DataFrame.select_dtypes)([include, exclude]) | Return a subset of the DataFrame's columns based on the column dtypes. |
| [`DataFrame.shape`](generated/maxframe.dataframe.DataFrame.shape.md#maxframe.dataframe.DataFrame.shape)                                             |                                                                        |

## Conversion

| [`DataFrame.astype`](generated/maxframe.dataframe.DataFrame.astype.md#maxframe.dataframe.DataFrame.astype)(dtype[, copy, errors])                        | Cast a pandas object to a specified dtype `dtype`.                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`DataFrame.convert_dtypes`](generated/maxframe.dataframe.DataFrame.convert_dtypes.md#maxframe.dataframe.DataFrame.convert_dtypes)([infer_objects, ...]) | Convert columns to best possible dtypes using dtypes supporting `pd.NA`. |
| [`DataFrame.copy`](generated/maxframe.dataframe.DataFrame.copy.md#maxframe.dataframe.DataFrame.copy)()                                                   |                                                                          |
| [`DataFrame.infer_objects`](generated/maxframe.dataframe.DataFrame.infer_objects.md#maxframe.dataframe.DataFrame.infer_objects)([copy])                  | Attempt to infer better dtypes for object columns.                       |

## Indexing, iteration

| [`DataFrame.at`](generated/maxframe.dataframe.DataFrame.at.md#maxframe.dataframe.DataFrame.at)                                          | Access a single value for a row/column label pair.                 |
|-----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`DataFrame.head`](generated/maxframe.dataframe.DataFrame.head.md#maxframe.dataframe.DataFrame.head)([n])                               | Return the first n rows.                                           |
| [`DataFrame.iat`](generated/maxframe.dataframe.DataFrame.iat.md#maxframe.dataframe.DataFrame.iat)                                       | Access a single value for a row/column pair by integer position.   |
| [`DataFrame.iloc`](generated/maxframe.dataframe.DataFrame.iloc.md#maxframe.dataframe.DataFrame.iloc)                                    | Purely integer-location based indexing for selection by position.  |
| [`DataFrame.insert`](generated/maxframe.dataframe.DataFrame.insert.md#maxframe.dataframe.DataFrame.insert)(loc, column, value[, ...])   | Insert column into DataFrame at specified location.                |
| [`DataFrame.loc`](generated/maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)                                       | Access a group of rows and columns by label(s) or a boolean array. |
| [`DataFrame.mask`](generated/maxframe.dataframe.DataFrame.mask.md#maxframe.dataframe.DataFrame.mask)(cond[, other, inplace, axis, ...]) | Replace values where the condition is True.                        |
| [`DataFrame.pop`](generated/maxframe.dataframe.DataFrame.pop.md#maxframe.dataframe.DataFrame.pop)(item)                                 | Return item and drop from frame.                                   |
| [`DataFrame.query`](generated/maxframe.dataframe.DataFrame.query.md#maxframe.dataframe.DataFrame.query)(expr[, inplace])                | Query the columns of a DataFrame with a boolean expression.        |
| [`DataFrame.tail`](generated/maxframe.dataframe.DataFrame.tail.md#maxframe.dataframe.DataFrame.tail)([n])                               | Return the last n rows.                                            |
| [`DataFrame.xs`](generated/maxframe.dataframe.DataFrame.xs.md#maxframe.dataframe.DataFrame.xs)(key[, axis, level, drop_level])          | Return cross-section from the Series/DataFrame.                    |
| [`DataFrame.where`](generated/maxframe.dataframe.DataFrame.where.md#maxframe.dataframe.DataFrame.where)(cond[, other, inplace, ...])    | Replace values where the condition is False.                       |

## Binary operator functions

| [`DataFrame.add`](generated/maxframe.dataframe.DataFrame.add.md#maxframe.dataframe.DataFrame.add)(other[, axis, level, fill_value])            | Get Addition of dataframe and other, element-wise (binary operator add).                |
|------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| [`DataFrame.sub`](generated/maxframe.dataframe.DataFrame.sub.md#maxframe.dataframe.DataFrame.sub)(other[, axis, level, fill_value])            | Get Subtraction of dataframe and other, element-wise (binary operator subtract).        |
| [`DataFrame.mul`](generated/maxframe.dataframe.DataFrame.mul.md#maxframe.dataframe.DataFrame.mul)(other[, axis, level, fill_value])            | Get Multiplication of dataframe and other, element-wise (binary operator mul).          |
| [`DataFrame.div`](generated/maxframe.dataframe.DataFrame.div.md#maxframe.dataframe.DataFrame.div)(other[, axis, level, fill_value])            | Get Floating division of dataframe and other, element-wise (binary operator truediv).   |
| [`DataFrame.truediv`](generated/maxframe.dataframe.DataFrame.truediv.md#maxframe.dataframe.DataFrame.truediv)(other[, axis, level, ...])       | Get Floating division of dataframe and other, element-wise (binary operator truediv).   |
| [`DataFrame.floordiv`](generated/maxframe.dataframe.DataFrame.floordiv.md#maxframe.dataframe.DataFrame.floordiv)(other[, axis, level, ...])    | Get Integer division of dataframe and other, element-wise (binary operator floordiv).   |
| [`DataFrame.mod`](generated/maxframe.dataframe.DataFrame.mod.md#maxframe.dataframe.DataFrame.mod)(other[, axis, level, fill_value])            | Get Modulo of dataframe and other, element-wise (binary operator mod).                  |
| [`DataFrame.pow`](generated/maxframe.dataframe.DataFrame.pow.md#maxframe.dataframe.DataFrame.pow)(other[, axis, level, fill_value])            | Get Exponential power of dataframe and other, element-wise (binary operator pow).       |
| [`DataFrame.dot`](generated/maxframe.dataframe.DataFrame.dot.md#maxframe.dataframe.DataFrame.dot)(other)                                       | Compute the matrix multiplication between the DataFrame and other.                      |
| [`DataFrame.radd`](generated/maxframe.dataframe.DataFrame.radd.md#maxframe.dataframe.DataFrame.radd)(other[, axis, level, fill_value])         | Get Addition of dataframe and other, element-wise (binary operator radd).               |
| [`DataFrame.rsub`](generated/maxframe.dataframe.DataFrame.rsub.md#maxframe.dataframe.DataFrame.rsub)(other[, axis, level, fill_value])         | Get Subtraction of dataframe and other, element-wise (binary operator rsubtract).       |
| [`DataFrame.rmul`](generated/maxframe.dataframe.DataFrame.rmul.md#maxframe.dataframe.DataFrame.rmul)(other[, axis, level, fill_value])         | Get Multiplication of dataframe and other, element-wise (binary operator rmul).         |
| [`DataFrame.rdiv`](generated/maxframe.dataframe.DataFrame.rdiv.md#maxframe.dataframe.DataFrame.rdiv)(other[, axis, level, fill_value])         | Get Floating division of dataframe and other, element-wise (binary operator rtruediv).  |
| [`DataFrame.rtruediv`](generated/maxframe.dataframe.DataFrame.rtruediv.md#maxframe.dataframe.DataFrame.rtruediv)(other[, axis, level, ...])    | Get Floating division of dataframe and other, element-wise (binary operator rtruediv).  |
| [`DataFrame.rfloordiv`](generated/maxframe.dataframe.DataFrame.rfloordiv.md#maxframe.dataframe.DataFrame.rfloordiv)(other[, axis, level, ...]) | Get Integer division of dataframe and other, element-wise (binary operator rfloordiv).  |
| [`DataFrame.rmod`](generated/maxframe.dataframe.DataFrame.rmod.md#maxframe.dataframe.DataFrame.rmod)(other[, axis, level, fill_value])         | Get Modulo of dataframe and other, element-wise (binary operator rmod).                 |
| [`DataFrame.rpow`](generated/maxframe.dataframe.DataFrame.rpow.md#maxframe.dataframe.DataFrame.rpow)(other[, axis, level, fill_value])         | Get Exponential power of dataframe and other, element-wise (binary operator rpow).      |
| [`DataFrame.lt`](generated/maxframe.dataframe.DataFrame.lt.md#maxframe.dataframe.DataFrame.lt)(other[, axis, level, fill_value])               | Get Less than of dataframe and other, element-wise (binary operator lt).                |
| [`DataFrame.gt`](generated/maxframe.dataframe.DataFrame.gt.md#maxframe.dataframe.DataFrame.gt)(other[, axis, level, fill_value])               | Get Greater than of dataframe and other, element-wise (binary operator gt).             |
| [`DataFrame.le`](generated/maxframe.dataframe.DataFrame.le.md#maxframe.dataframe.DataFrame.le)(other[, axis, level, fill_value])               | Get Less than or equal to of dataframe and other, element-wise (binary operator le).    |
| [`DataFrame.ge`](generated/maxframe.dataframe.DataFrame.ge.md#maxframe.dataframe.DataFrame.ge)(other[, axis, level, fill_value])               | Get Greater than or equal to of dataframe and other, element-wise (binary operator ge). |
| [`DataFrame.ne`](generated/maxframe.dataframe.DataFrame.ne.md#maxframe.dataframe.DataFrame.ne)(other[, axis, level, fill_value])               | Get Not equal to of dataframe and other, element-wise (binary operator ne).             |
| [`DataFrame.eq`](generated/maxframe.dataframe.DataFrame.eq.md#maxframe.dataframe.DataFrame.eq)(other[, axis, level, fill_value])               | Get Equal to of dataframe and other, element-wise (binary operator eq).                 |
| [`DataFrame.combine`](generated/maxframe.dataframe.DataFrame.combine.md#maxframe.dataframe.DataFrame.combine)(other, func[, fill_value, ...])  | Perform column-wise combine with another DataFrame.                                     |
| [`DataFrame.combine_first`](generated/maxframe.dataframe.DataFrame.combine_first.md#maxframe.dataframe.DataFrame.combine_first)(other)         | Update null elements with value in the same location in other.                          |

## Function application, GroupBy & window

| [`DataFrame.apply`](generated/maxframe.dataframe.DataFrame.apply.md#maxframe.dataframe.DataFrame.apply)(func[, axis, raw, ...])                | Apply a function along an axis of the DataFrame.                   |
|------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`DataFrame.applymap`](generated/maxframe.dataframe.DataFrame.applymap.md#maxframe.dataframe.DataFrame.applymap)(func[, na_action, ...])       | Apply a function to a Dataframe elementwise.                       |
| [`DataFrame.agg`](generated/maxframe.dataframe.DataFrame.agg.md#maxframe.dataframe.DataFrame.agg)([func, axis])                                | Aggregate using one or more operations over the specified axis.    |
| [`DataFrame.aggregate`](generated/maxframe.dataframe.DataFrame.aggregate.md#maxframe.dataframe.DataFrame.aggregate)([func, axis])              | Aggregate using one or more operations over the specified axis.    |
| [`DataFrame.ewm`](generated/maxframe.dataframe.DataFrame.ewm.md#maxframe.dataframe.DataFrame.ewm)([com, span, halflife, alpha, ...])           | Provide exponential weighted functions.                            |
| [`DataFrame.expanding`](generated/maxframe.dataframe.DataFrame.expanding.md#maxframe.dataframe.DataFrame.expanding)([min_periods, shift, ...]) | Provide expanding transformations.                                 |
| [`DataFrame.groupby`](generated/maxframe.dataframe.DataFrame.groupby.md#maxframe.dataframe.DataFrame.groupby)([by, level, as_index, ...])      | Group DataFrame using a mapper or by a Series of columns.          |
| [`DataFrame.map`](generated/maxframe.dataframe.DataFrame.map.md#maxframe.dataframe.DataFrame.map)(func[, na_action, dtypes, ...])              | Apply a function to a Dataframe elementwise.                       |
| [`DataFrame.rolling`](generated/maxframe.dataframe.DataFrame.rolling.md#maxframe.dataframe.DataFrame.rolling)(window[, min_periods, ...])      | Provide rolling window calculations.                               |
| [`DataFrame.transform`](generated/maxframe.dataframe.DataFrame.transform.md#maxframe.dataframe.DataFrame.transform)(func[, axis, dtypes, ...]) | Call `func` on self producing a DataFrame with transformed values. |

<a id="generated-dataframe-stats"></a>

## Computations / descriptive stats

| [`DataFrame.abs`](generated/maxframe.dataframe.DataFrame.abs.md#maxframe.dataframe.DataFrame.abs)()                                                    |                                                                    |
|--------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`DataFrame.all`](generated/maxframe.dataframe.DataFrame.all.md#maxframe.dataframe.DataFrame.all)([axis, bool_only, skipna, ...])                      |                                                                    |
| [`DataFrame.any`](generated/maxframe.dataframe.DataFrame.any.md#maxframe.dataframe.DataFrame.any)([axis, bool_only, skipna, ...])                      |                                                                    |
| [`DataFrame.clip`](generated/maxframe.dataframe.DataFrame.clip.md#maxframe.dataframe.DataFrame.clip)([lower, upper, axis, inplace])                    | Trim values at input threshold(s).                                 |
| [`DataFrame.count`](generated/maxframe.dataframe.DataFrame.count.md#maxframe.dataframe.DataFrame.count)([axis, level, numeric_only])                   |                                                                    |
| [`DataFrame.corr`](generated/maxframe.dataframe.DataFrame.corr.md#maxframe.dataframe.DataFrame.corr)([method, min_periods])                            | Compute pairwise correlation of columns, excluding NA/null values. |
| [`DataFrame.corrwith`](generated/maxframe.dataframe.DataFrame.corrwith.md#maxframe.dataframe.DataFrame.corrwith)(other[, axis, drop, method])          | Compute pairwise correlation.                                      |
| [`DataFrame.cov`](generated/maxframe.dataframe.DataFrame.cov.md#maxframe.dataframe.DataFrame.cov)([min_periods, ddof, numeric_only])                   | Compute pairwise covariance of columns, excluding NA/null values.  |
| [`DataFrame.describe`](generated/maxframe.dataframe.DataFrame.describe.md#maxframe.dataframe.DataFrame.describe)([percentiles, include, ...])          | Generate descriptive statistics.                                   |
| [`DataFrame.diff`](generated/maxframe.dataframe.DataFrame.diff.md#maxframe.dataframe.DataFrame.diff)([periods, axis])                                  | First discrete difference of element.                              |
| [`DataFrame.eval`](generated/maxframe.dataframe.DataFrame.eval.md#maxframe.dataframe.DataFrame.eval)(expr[, inplace])                                  | Evaluate a string describing operations on DataFrame columns.      |
| [`DataFrame.max`](generated/maxframe.dataframe.DataFrame.max.md#maxframe.dataframe.DataFrame.max)([axis, skipna, level, ...])                          |                                                                    |
| [`DataFrame.mean`](generated/maxframe.dataframe.DataFrame.mean.md#maxframe.dataframe.DataFrame.mean)([axis, skipna, level, ...])                       |                                                                    |
| [`DataFrame.median`](generated/maxframe.dataframe.DataFrame.median.md#maxframe.dataframe.DataFrame.median)([axis, skipna, level, ...])                 |                                                                    |
| [`DataFrame.min`](generated/maxframe.dataframe.DataFrame.min.md#maxframe.dataframe.DataFrame.min)([axis, skipna, level, ...])                          |                                                                    |
| [`DataFrame.mode`](generated/maxframe.dataframe.DataFrame.mode.md#maxframe.dataframe.DataFrame.mode)([axis, numeric_only, dropna, ...])                | Get the mode(s) of each element along the selected axis.           |
| [`DataFrame.nunique`](generated/maxframe.dataframe.DataFrame.nunique.md#maxframe.dataframe.DataFrame.nunique)([axis, dropna])                          | Count distinct observations over requested axis.                   |
| [`DataFrame.pct_change`](generated/maxframe.dataframe.DataFrame.pct_change.md#maxframe.dataframe.DataFrame.pct_change)([periods, fill_method, ...])    | Percentage change between the current and a prior element.         |
| [`DataFrame.prod`](generated/maxframe.dataframe.DataFrame.prod.md#maxframe.dataframe.DataFrame.prod)([axis, skipna, level, ...])                       |                                                                    |
| [`DataFrame.product`](generated/maxframe.dataframe.DataFrame.product.md#maxframe.dataframe.DataFrame.product)([axis, skipna, level, ...])              |                                                                    |
| [`DataFrame.quantile`](generated/maxframe.dataframe.DataFrame.quantile.md#maxframe.dataframe.DataFrame.quantile)([q, axis, numeric_only, ...])         | Return values at the given quantile over requested axis.           |
| [`DataFrame.rank`](generated/maxframe.dataframe.DataFrame.rank.md#maxframe.dataframe.DataFrame.rank)([axis, method, numeric_only, ...])                | Compute numerical data ranks (1 through n) along axis.             |
| [`DataFrame.round`](generated/maxframe.dataframe.DataFrame.round.md#maxframe.dataframe.DataFrame.round)([decimals])                                    | Round a DataFrame to a variable number of decimal places.          |
| [`DataFrame.sem`](generated/maxframe.dataframe.DataFrame.sem.md#maxframe.dataframe.DataFrame.sem)([axis, skipna, level, ddof, ...])                    |                                                                    |
| [`DataFrame.std`](generated/maxframe.dataframe.DataFrame.std.md#maxframe.dataframe.DataFrame.std)([axis, skipna, level, ddof, ...])                    |                                                                    |
| [`DataFrame.sum`](generated/maxframe.dataframe.DataFrame.sum.md#maxframe.dataframe.DataFrame.sum)([axis, skipna, level, ...])                          |                                                                    |
| [`DataFrame.value_counts`](generated/maxframe.dataframe.DataFrame.value_counts.md#maxframe.dataframe.DataFrame.value_counts)([subset, normalize, ...]) |                                                                    |
| [`DataFrame.var`](generated/maxframe.dataframe.DataFrame.var.md#maxframe.dataframe.DataFrame.var)([axis, skipna, level, ddof, ...])                    |                                                                    |

## Reindexing / selection / label manipulation

| [`DataFrame.add_prefix`](generated/maxframe.dataframe.DataFrame.add_prefix.md#maxframe.dataframe.DataFrame.add_prefix)(prefix)                             | Prefix labels with string prefix.                                             |
|------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`DataFrame.add_suffix`](generated/maxframe.dataframe.DataFrame.add_suffix.md#maxframe.dataframe.DataFrame.add_suffix)(suffix)                             | Suffix labels with string suffix.                                             |
| [`DataFrame.align`](generated/maxframe.dataframe.DataFrame.align.md#maxframe.dataframe.DataFrame.align)(other[, join, axis, level, ...])                   | Align two objects on their axes with the specified join method.               |
| [`DataFrame.at_time`](generated/maxframe.dataframe.DataFrame.at_time.md#maxframe.dataframe.DataFrame.at_time)(time[, axis])                                | Select values at particular time of day (e.g., 9:30AM).                       |
| [`DataFrame.between_time`](generated/maxframe.dataframe.DataFrame.between_time.md#maxframe.dataframe.DataFrame.between_time)(start_time, end_time)         | Select values between particular times of the day (e.g., 9:00-9:30 AM).       |
| [`DataFrame.drop`](generated/maxframe.dataframe.DataFrame.drop.md#maxframe.dataframe.DataFrame.drop)([labels, axis, index, ...])                           | Drop specified labels from rows or columns.                                   |
| [`DataFrame.drop_duplicates`](generated/maxframe.dataframe.DataFrame.drop_duplicates.md#maxframe.dataframe.DataFrame.drop_duplicates)([subset, keep, ...]) | Return DataFrame with duplicate rows removed.                                 |
| [`DataFrame.droplevel`](generated/maxframe.dataframe.DataFrame.droplevel.md#maxframe.dataframe.DataFrame.droplevel)(level[, axis])                         | Return Series/DataFrame with requested index / column level(s) removed.       |
| [`DataFrame.duplicated`](generated/maxframe.dataframe.DataFrame.duplicated.md#maxframe.dataframe.DataFrame.duplicated)([subset, keep, method])             | Return boolean Series denoting duplicate rows.                                |
| [`DataFrame.filter`](generated/maxframe.dataframe.DataFrame.filter.md#maxframe.dataframe.DataFrame.filter)([items, like, regex, axis])                     | Subset the dataframe rows or columns according to the specified index labels. |
| [`DataFrame.head`](generated/maxframe.dataframe.DataFrame.head.md#maxframe.dataframe.DataFrame.head)([n])                                                  | Return the first n rows.                                                      |
| [`DataFrame.idxmax`](generated/maxframe.dataframe.DataFrame.idxmax.md#maxframe.dataframe.DataFrame.idxmax)([axis, skipna])                                 | Return index of first occurrence of maximum over requested axis.              |
| [`DataFrame.idxmin`](generated/maxframe.dataframe.DataFrame.idxmin.md#maxframe.dataframe.DataFrame.idxmin)([axis, skipna])                                 | Return index of first occurrence of minimum over requested axis.              |
| [`DataFrame.reindex`](generated/maxframe.dataframe.DataFrame.reindex.md#maxframe.dataframe.DataFrame.reindex)([labels, index, columns, ...])               | Conform Series/DataFrame to new index with optional filling logic.            |
| [`DataFrame.reindex_like`](generated/maxframe.dataframe.DataFrame.reindex_like.md#maxframe.dataframe.DataFrame.reindex_like)(other[, method, ...])         | Return an object with matching indices as other object.                       |
| [`DataFrame.rename`](generated/maxframe.dataframe.DataFrame.rename.md#maxframe.dataframe.DataFrame.rename)([mapper, index, columns, ...])                  | Alter axes labels.                                                            |
| [`DataFrame.rename_axis`](generated/maxframe.dataframe.DataFrame.rename_axis.md#maxframe.dataframe.DataFrame.rename_axis)([mapper, index, ...])            | Set the name of the axis for the index or columns.                            |
| [`DataFrame.reset_index`](generated/maxframe.dataframe.DataFrame.reset_index.md#maxframe.dataframe.DataFrame.reset_index)([level, drop, ...])              | Reset the index, or a level of it.                                            |
| [`DataFrame.sample`](generated/maxframe.dataframe.DataFrame.sample.md#maxframe.dataframe.DataFrame.sample)([n, frac, replace, ...])                        | Return a random sample of items from an axis of object.                       |
| [`DataFrame.set_axis`](generated/maxframe.dataframe.DataFrame.set_axis.md#maxframe.dataframe.DataFrame.set_axis)(labels[, axis, inplace])                  | Assign desired index to given axis.                                           |
| [`DataFrame.set_index`](generated/maxframe.dataframe.DataFrame.set_index.md#maxframe.dataframe.DataFrame.set_index)(keys[, drop, append, ...])             | Set the DataFrame index using existing columns.                               |
| [`DataFrame.take`](generated/maxframe.dataframe.DataFrame.take.md#maxframe.dataframe.DataFrame.take)(indices[, axis])                                      | Return the elements in the given *positional* indices along an axis.          |
| [`DataFrame.truncate`](generated/maxframe.dataframe.DataFrame.truncate.md#maxframe.dataframe.DataFrame.truncate)([before, after, axis, copy])              | Truncate a Series or DataFrame before and after some index value.             |

<a id="generated-dataframe-missing"></a>

## Missing data handling

| [`DataFrame.dropna`](generated/maxframe.dataframe.DataFrame.dropna.md#maxframe.dataframe.DataFrame.dropna)([axis, how, thresh, ...])   | Remove missing values.                         |
|----------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| [`DataFrame.fillna`](generated/maxframe.dataframe.DataFrame.fillna.md#maxframe.dataframe.DataFrame.fillna)([value, method, axis, ...]) | Fill NA/NaN values using the specified method. |
| [`DataFrame.isna`](generated/maxframe.dataframe.DataFrame.isna.md#maxframe.dataframe.DataFrame.isna)()                                 | Detect missing values.                         |
| [`DataFrame.isnull`](generated/maxframe.dataframe.DataFrame.isnull.md#maxframe.dataframe.DataFrame.isnull)()                           | Detect missing values.                         |
| [`DataFrame.notna`](generated/maxframe.dataframe.DataFrame.notna.md#maxframe.dataframe.DataFrame.notna)()                              | Detect existing (non-missing) values.          |
| [`DataFrame.notnull`](generated/maxframe.dataframe.DataFrame.notnull.md#maxframe.dataframe.DataFrame.notnull)()                        | Detect existing (non-missing) values.          |

## Reshaping, sorting, transposing

| [`DataFrame.melt`](generated/maxframe.dataframe.DataFrame.melt.md#maxframe.dataframe.DataFrame.melt)([id_vars, value_vars, ...])                      | Unpivot a DataFrame from wide to long format, optionally leaving identifiers set.   |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`DataFrame.nlargest`](generated/maxframe.dataframe.DataFrame.nlargest.md#maxframe.dataframe.DataFrame.nlargest)(n, columns[, keep])                  | Return the first n rows ordered by columns in descending order.                     |
| [`DataFrame.nsmallest`](generated/maxframe.dataframe.DataFrame.nsmallest.md#maxframe.dataframe.DataFrame.nsmallest)(n, columns[, keep])               | Return the first n rows ordered by columns in ascending order.                      |
| [`DataFrame.pivot`](generated/maxframe.dataframe.DataFrame.pivot.md#maxframe.dataframe.DataFrame.pivot)(columns[, index, values])                     | Return reshaped DataFrame organized by given index / column values.                 |
| [`DataFrame.pivot_table`](generated/maxframe.dataframe.DataFrame.pivot_table.md#maxframe.dataframe.DataFrame.pivot_table)([values, index, ...])       | Create a spreadsheet-style pivot table as a DataFrame.                              |
| [`DataFrame.reorder_levels`](generated/maxframe.dataframe.DataFrame.reorder_levels.md#maxframe.dataframe.DataFrame.reorder_levels)(order[, axis])     | Rearrange index levels using input order.                                           |
| [`DataFrame.sort_values`](generated/maxframe.dataframe.DataFrame.sort_values.md#maxframe.dataframe.DataFrame.sort_values)(by[, axis, ascending, ...]) | Sort by the values along either axis.                                               |
| [`DataFrame.sort_index`](generated/maxframe.dataframe.DataFrame.sort_index.md#maxframe.dataframe.DataFrame.sort_index)([axis, level, ...])            | Sort object by labels (along an axis).                                              |
| [`DataFrame.swaplevel`](generated/maxframe.dataframe.DataFrame.swaplevel.md#maxframe.dataframe.DataFrame.swaplevel)([i, j, axis])                     | Swap levels i and j in a `MultiIndex`.                                              |
| [`DataFrame.stack`](generated/maxframe.dataframe.DataFrame.stack.md#maxframe.dataframe.DataFrame.stack)([level, dropna])                              | Stack the prescribed level(s) from columns to index.                                |
| [`DataFrame.unstack`](generated/maxframe.dataframe.DataFrame.unstack.md#maxframe.dataframe.DataFrame.unstack)([level, fill_value])                    | Unstack, also known as pivot, Series with MultiIndex to produce DataFrame.          |

## Combining / comparing / joining / merging

| [`DataFrame.append`](generated/maxframe.dataframe.DataFrame.append.md#maxframe.dataframe.DataFrame.append)(other[, ignore_index, ...])    | Append rows of other to the end of caller, returning a new object.   |
|-------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`DataFrame.assign`](generated/maxframe.dataframe.DataFrame.assign.md#maxframe.dataframe.DataFrame.assign)(\*\*kwargs)                    | Assign new columns to a DataFrame.                                   |
| [`DataFrame.compare`](generated/maxframe.dataframe.DataFrame.compare.md#maxframe.dataframe.DataFrame.compare)(other[, align_axis, ...])   | Compare to another DataFrame and show the differences.               |
| [`DataFrame.join`](generated/maxframe.dataframe.DataFrame.join.md#maxframe.dataframe.DataFrame.join)(other[, on, how, lsuffix, ...])      | Join columns of another DataFrame.                                   |
| [`DataFrame.merge`](generated/maxframe.dataframe.DataFrame.merge.md#maxframe.dataframe.DataFrame.merge)(right[, how, on, left_on, ...])   | Merge DataFrame or named Series objects with a database-style join.  |
| [`DataFrame.update`](generated/maxframe.dataframe.DataFrame.update.md#maxframe.dataframe.DataFrame.update)(other[, join, overwrite, ...]) | Modify in place using non-NA values from another DataFrame.          |

### Time series-related

| [`DataFrame.first_valid_index`](generated/maxframe.dataframe.DataFrame.first_valid_index.md#maxframe.dataframe.DataFrame.first_valid_index)()   | Return index for first non-NA value or None, if no non-NA value is found.   |
|-------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`DataFrame.last_valid_index`](generated/maxframe.dataframe.DataFrame.last_valid_index.md#maxframe.dataframe.DataFrame.last_valid_index)()      | Return index for last non-NA value or None, if no non-NA value is found.    |
| [`DataFrame.shift`](generated/maxframe.dataframe.DataFrame.shift.md#maxframe.dataframe.DataFrame.shift)([periods, freq, axis, ...])             | Shift index by desired number of periods with an optional time freq.        |
| [`DataFrame.tshift`](generated/maxframe.dataframe.DataFrame.tshift.md#maxframe.dataframe.DataFrame.tshift)([periods, freq, axis])               | Shift the time index, using the index's frequency if available.             |

<a id="generated-dataframe-plotting"></a>

## Plotting

`DataFrame.plot` is both a callable method and a namespace attribute for
specific plotting methods of the form `DataFrame.plot.<kind>`.

| [`DataFrame.plot`](generated/maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot)   | alias of `DataFramePlotAccessor`   |
|--------------------------------------------------------------------------------------------------------|------------------------------------|

| [`DataFrame.plot.area`](generated/maxframe.dataframe.DataFrame.plot.area.md#maxframe.dataframe.DataFrame.plot.area)(\*args, \*\*kwargs)          | Draw a stacked area plot.                                       |
|--------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`DataFrame.plot.bar`](generated/maxframe.dataframe.DataFrame.plot.bar.md#maxframe.dataframe.DataFrame.plot.bar)(\*args, \*\*kwargs)             | Vertical bar plot.                                              |
| [`DataFrame.plot.barh`](generated/maxframe.dataframe.DataFrame.plot.barh.md#maxframe.dataframe.DataFrame.plot.barh)(\*args, \*\*kwargs)          | Make a horizontal bar plot.                                     |
| [`DataFrame.plot.box`](generated/maxframe.dataframe.DataFrame.plot.box.md#maxframe.dataframe.DataFrame.plot.box)(\*args, \*\*kwargs)             | Make a box plot of the DataFrame columns.                       |
| [`DataFrame.plot.density`](generated/maxframe.dataframe.DataFrame.plot.density.md#maxframe.dataframe.DataFrame.plot.density)(\*args, \*\*kwargs) | Generate Kernel Density Estimate plot using Gaussian kernels.   |
| [`DataFrame.plot.hexbin`](generated/maxframe.dataframe.DataFrame.plot.hexbin.md#maxframe.dataframe.DataFrame.plot.hexbin)(\*args, \*\*kwargs)    | Generate a hexagonal binning plot.                              |
| [`DataFrame.plot.hist`](generated/maxframe.dataframe.DataFrame.plot.hist.md#maxframe.dataframe.DataFrame.plot.hist)(\*args, \*\*kwargs)          | Draw one histogram of the DataFrame's columns.                  |
| [`DataFrame.plot.kde`](generated/maxframe.dataframe.DataFrame.plot.kde.md#maxframe.dataframe.DataFrame.plot.kde)(\*args, \*\*kwargs)             | Generate Kernel Density Estimate plot using Gaussian kernels.   |
| [`DataFrame.plot.line`](generated/maxframe.dataframe.DataFrame.plot.line.md#maxframe.dataframe.DataFrame.plot.line)(\*args, \*\*kwargs)          | Plot Series or DataFrame as lines.                              |
| [`DataFrame.plot.pie`](generated/maxframe.dataframe.DataFrame.plot.pie.md#maxframe.dataframe.DataFrame.plot.pie)(\*args, \*\*kwargs)             | Generate a pie plot.                                            |
| [`DataFrame.plot.scatter`](generated/maxframe.dataframe.DataFrame.plot.scatter.md#maxframe.dataframe.DataFrame.plot.scatter)(\*args, \*\*kwargs) | Create a scatter plot with varying marker point size and color. |

<a id="generated-dataframe-io"></a>

## Serialization / IO / conversion

| [`DataFrame.from_dict`](generated/maxframe.dataframe.DataFrame.from_dict.md#maxframe.dataframe.DataFrame.from_dict)(data[, orient, dtype, ...])          | Construct DataFrame from dict of array-like or dicts.                                         |
|----------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [`DataFrame.from_records`](generated/maxframe.dataframe.DataFrame.from_records.md#maxframe.dataframe.DataFrame.from_records)(data[, index, ...])         | Convert structured or record ndarray to DataFrame.                                            |
| [`DataFrame.to_clipboard`](generated/maxframe.dataframe.DataFrame.to_clipboard.md#maxframe.dataframe.DataFrame.to_clipboard)(\*[, excel, sep, ...])      | Copy object to the system clipboard.                                                          |
| [`DataFrame.to_csv`](generated/maxframe.dataframe.DataFrame.to_csv.md#maxframe.dataframe.DataFrame.to_csv)(path[, sep, na_rep, ...])                     | Write object to a comma-separated values (csv) file.                                          |
| [`DataFrame.to_dict`](generated/maxframe.dataframe.DataFrame.to_dict.md#maxframe.dataframe.DataFrame.to_dict)([orient, into, index, ...])                | Convert the DataFrame to a dictionary.                                                        |
| [`DataFrame.to_json`](generated/maxframe.dataframe.DataFrame.to_json.md#maxframe.dataframe.DataFrame.to_json)([path, orient, ...])                       | Convert the object to a JSON string.                                                          |
| [`DataFrame.to_odps_table`](generated/maxframe.dataframe.DataFrame.to_odps_table.md#maxframe.dataframe.DataFrame.to_odps_table)(table[, partition, ...]) | Write DataFrame object into a MaxCompute (ODPS) table.                                        |
| [`DataFrame.to_pandas`](generated/maxframe.dataframe.DataFrame.to_pandas.md#maxframe.dataframe.DataFrame.to_pandas)([session])                           |                                                                                               |
| [`DataFrame.to_parquet`](generated/maxframe.dataframe.DataFrame.to_parquet.md#maxframe.dataframe.DataFrame.to_parquet)(path[, engine, ...])              | Write a DataFrame to the binary parquet format, each chunk will be written to a Parquet file. |

<a id="generated-dataframe-mf"></a>

## MaxFrame Extensions

| [`DataFrame.mf.apply_chunk`](generated/maxframe.dataframe.DataFrame.mf.apply_chunk.md#maxframe.dataframe.DataFrame.mf.apply_chunk)(func[, batch_rows, ...])   | Apply a function that takes pandas DataFrame and outputs pandas DataFrame/Series.   |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`DataFrame.mf.collect_kv`](generated/maxframe.dataframe.DataFrame.mf.collect_kv.md#maxframe.dataframe.DataFrame.mf.collect_kv)([columns, kv_delim, ...])     | Merge values in specified columns into a key-value represented column.              |
| [`DataFrame.mf.extract_kv`](generated/maxframe.dataframe.DataFrame.mf.extract_kv.md#maxframe.dataframe.DataFrame.mf.extract_kv)([columns, kv_delim, ...])     | Extract values in key-value represented columns into standalone columns.            |
| [`DataFrame.mf.flatmap`](generated/maxframe.dataframe.DataFrame.mf.flatmap.md#maxframe.dataframe.DataFrame.mf.flatmap)(func[, dtypes, raw, args])             | Apply the given function to each row and then flatten results.                      |
| [`DataFrame.mf.map_reduce`](generated/maxframe.dataframe.DataFrame.mf.map_reduce.md#maxframe.dataframe.DataFrame.mf.map_reduce)([mapper, reducer, ...])       | Map-reduce API over certain DataFrames.                                             |
| [`DataFrame.mf.rebalance`](generated/maxframe.dataframe.DataFrame.mf.rebalance.md#maxframe.dataframe.DataFrame.mf.rebalance)([axis, factor, ...])             | Make data more balanced across entire cluster.                                      |
| [`DataFrame.mf.reshuffle`](generated/maxframe.dataframe.DataFrame.mf.reshuffle.md#maxframe.dataframe.DataFrame.mf.reshuffle)([group_by, sort_by, ...])        | Shuffle data in DataFrame or Series to make data distribution more randomized.      |

`DataFrame.mf` provides methods unique to MaxFrame. These methods are collated from application
scenarios in MaxCompute and these can be accessed like `DataFrame.mf.<function/property>`.
