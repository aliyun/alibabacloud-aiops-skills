# maxframe.dataframe.Series.describe

#### Series.describe(percentiles=None, include=None, exclude=None)

Generate descriptive statistics.

Descriptive statistics include those that summarize the central
tendency, dispersion and shape of a
dataset’s distribution, excluding `NaN` values.

Analyzes both numeric and object series, as well
as `DataFrame` column sets of mixed data types. The output
will vary depending on what is provided. Refer to the notes
below for more detail.

* **Parameters:**
  * **percentiles** (*list-like* *of* *numbers* *,* *optional*) – The percentiles to include in the output. All should
    fall between 0 and 1. The default is
    `[.25, .5, .75]`, which returns the 25th, 50th, and
    75th percentiles.
  * **include** ( *'all'* *,* *list-like* *of* *dtypes* *or* *None* *(**default* *)* *,* *optional*) – 

    A white list of data types to include in the result. Ignored
    for `Series`. Here are the options:
    - ’all’ : All columns of the input will be included in the output.
    - A list-like of dtypes : Limits the results to the
      provided data types.
      To limit the result to numeric types submit
      `numpy.number`. To limit it instead to object columns submit
      the `numpy.object` data type. Strings
      can also be used in the style of
      `select_dtypes` (e.g. `df.describe(include=['O'])`).
    - None (default) : The result will include all numeric columns.
  * **exclude** (*list-like* *of* *dtypes* *or* *None* *(**default* *)* *,* *optional* *,*) – 

    A black list of data types to omit from the result. Ignored
    for `Series`. Here are the options:
    - A list-like of dtypes : Excludes the provided data types
      from the result. To exclude numeric types submit
      `numpy.number`. To exclude object columns submit the data
      type `numpy.object`. Strings can also be used in the style of
      `select_dtypes` (e.g. `df.describe(exclude=['O'])`).
    - None (default) : The result will exclude nothing.
* **Returns:**
  Summary statistics of the Series or Dataframe provided.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.count`](maxframe.dataframe.DataFrame.count.md#maxframe.dataframe.DataFrame.count)
: Count number of non-NA/null observations.

[`DataFrame.max`](maxframe.dataframe.DataFrame.max.md#maxframe.dataframe.DataFrame.max)
: Maximum of the values in the object.

[`DataFrame.min`](maxframe.dataframe.DataFrame.min.md#maxframe.dataframe.DataFrame.min)
: Minimum of the values in the object.

[`DataFrame.mean`](maxframe.dataframe.DataFrame.mean.md#maxframe.dataframe.DataFrame.mean)
: Mean of the values.

[`DataFrame.std`](maxframe.dataframe.DataFrame.std.md#maxframe.dataframe.DataFrame.std)
: Standard deviation of the observations.

[`DataFrame.select_dtypes`](maxframe.dataframe.DataFrame.select_dtypes.md#maxframe.dataframe.DataFrame.select_dtypes)
: Subset of a DataFrame including/excluding columns based on their dtype.

### Notes

For numeric data, the result’s index will include `count`,
`mean`, `std`, `min`, `max` as well as lower, `50` and
upper percentiles. By default the lower percentile is `25` and the
upper percentile is `75`. The `50` percentile is the
same as the median.

For object data (e.g. strings or timestamps), the result’s index
will include `count`, `unique`, `top`, and `freq`. The `top`
is the most common value. The `freq` is the most common value’s
frequency. Timestamps also include the `first` and `last` items.

If multiple object values have the highest count, then the
`count` and `top` results will be arbitrarily chosen from
among those with the highest count.

For mixed data types provided via a `DataFrame`, the default is to
return only an analysis of numeric columns. If the dataframe consists
only of object data without any numeric columns, the default is to
return an analysis of object columns. If `include='all'` is provided
as an option, the result will include a union of attributes of each type.

The include and exclude parameters can be used to limit
which columns in a `DataFrame` are analyzed for the output.
The parameters are ignored when analyzing a `Series`.

### Examples

Describing a numeric `Series`.

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.describe().execute()
count    3.0
mean     2.0
std      1.0
min      1.0
25%      1.5
50%      2.0
75%      2.5
max      3.0
dtype: float64
```

Describing a `DataFrame`. By default only numeric fields
are returned.

```pycon
>>> df = md.DataFrame({'numeric': [1, 2, 3],
...                    'object': ['a', 'b', 'c']
...                    })
>>> df.describe().execute()
       numeric
count      3.0
mean       2.0
std        1.0
min        1.0
25%        1.5
50%        2.0
75%        2.5
max        3.0
```

Describing all columns of a `DataFrame` regardless of data type.

```pycon
>>> df.describe(include='all').execute()
       numeric object
count      3.0      3
unique     NaN      3
top        NaN      a
freq       NaN      1
mean       2.0    NaN
std        1.0    NaN
min        1.0    NaN
25%        1.5    NaN
50%        2.0    NaN
75%        2.5    NaN
max        3.0    NaN
```

Describing a column from a `DataFrame` by accessing it as
an attribute.

```pycon
>>> df.numeric.describe().execute()
count    3.0
mean     2.0
std      1.0
min      1.0
25%      1.5
50%      2.0
75%      2.5
max      3.0
Name: numeric, dtype: float64
```

Including only numeric columns in a `DataFrame` description.

```pycon
>>> df.describe(include=[mt.number]).execute()
       numeric
count      3.0
mean       2.0
std        1.0
min        1.0
25%        1.5
50%        2.0
75%        2.5
max        3.0
```

Including only string columns in a `DataFrame` description.

```pycon
>>> df.describe(include=[object]).execute()
       object
count       3
unique      3
top         a
freq        1
```
