# Comparison with PyODPS DataFrame

[PyODPS DataFrame](https://pyodps.readthedocs.io/en/stable/df.html) is
a DataFrame-like package provided by MaxCompute as a part of PyODPS package.
It provides capability for Python data analyzers to query MaxCompute data
with a set of operators similar to pandas. Despite the similarity in operators,
the usage between two sets of APIs are quite different. It might not be easy
for a developer to dive deep into PyODPS DataFrame with knowledge about
pandas only.

Though PyODPS DataFrame is still part of PyODPS, it is recommended to create
new applications with MaxFrame to enjoy its compatibility with pandas.

## Object abstraction

PyODPS DataFrame does not have indexes. This means that a majority of pandas
APIs with indexes cannot be used or not fully supported.

For instance, arithmetic operations in pandas relies on index alignment. That
is, two DataFrames are aligned first, and then arithmetic operation is performed.

```python
>>> series1 = pd.Series([2, 1, 3], index=[1, 2, 4])
>>> series2 = pd.Series([1, 5, 6], index=[1, 3, 4])
>>> series1 + series2
1    3.0
2    NaN
3    NaN
4    9.0
dtype: float64
```

However, when indexes are absent, this kind of operation is not supported.

To support this kind of operation, in MaxFrame, it is required to add an index
column to DataFrame or Series. If the index is absent, a default RangeIndex
is added. Therefore the statement above can be supported.

Another huge difference between PyODPS DataFrame and MaxFrame is that in PyODPS
DataFrame, representation of data objects and operators are mixed, and this
may confuse newcomers. For instance,

```python
df = o.get_table('table_name').to_df()  # df is a DataFrame instance
df2 = df["col1", "col2"]  # df2 is a CollectionExpr instance
```

In the second line, `df2` is an instance of `CollectionExpr` which means
it is an expression and different from a `DataFrame` instance. However, all
DataFrame functions can be applied directly onto `df2` and there is nothing
different from `DataFrame` instance.

In MaxFrame, however, data objects and operators are defined separately. Data
objects users interact with are all instances of a few data classes, namely
`DataFrame`, `Series` or `Index`. For the example above, now all
instances are DataFrame now.

```python
df = md.read_odps_table('table_name')  # df is a DataFrame instance
df2 = df[["col1", "col2"]]  # df2 is also a DataFrame instance
```

## Functions

Functions in PyODPS DataFrame are not fully compatible with pandas. Therefore
to write code with PyODPS DataFrame, users need to read the documents first
before start coding. However, the target of MaxFrame is to create a pandas-compatible
API. Hence there are API differences between PyODPS DataFrame and MaxFrame.
These differences are listed below. Methods starts with `mf.` mean that these non-pandas
methods are added in MaxFrame to facilitate migrating from PyODPS DataFrame to MaxFrame.
Note that you need to read API documents of these functions before rewriting your code.

| PyODPS DataFrame API                | MaxFrame API                                    |
|-------------------------------------|-------------------------------------------------|
| DataFrame.append_id                 | Not needed. DataFrame index is added by default |
| DataFrame.bloom_filter              | Not implemented yet                             |
| DataFrame.boxplot                   | DataFrame.plot.boxplot                          |
| DataFrame.concat                    | maxframe.dataframe.concat                       |
| DataFrame.describe                  | DataFrame.describe                              |
| DataFrame.distinct                  | DataFrame.drop_duplicates                       |
| DataFrame.except_                   | DataFrame.merge with filter                     |
| DataFrame.exclude                   | DataFrame.drop                                  |
| DataFrame.extract_kv                | Not implemented yet                             |
| DataFrame.hist                      | DataFrame.plot.hist                             |
| DataFrame.inner_join                | DataFrame.merge                                 |
| DataFrame.intersect                 | DataFrame.merge                                 |
| DataFrame.left_join                 | DataFrame.merge                                 |
| DataFrame.limit                     | DataFrame.head                                  |
| DataFrame.map_reduce                | DataFrame.mf.map_reduce                         |
| DataFrame.minmax_scale              | Not implemented yet                             |
| DataFrame.outer_join                | DataFrame.merge                                 |
| DataFrame.persist                   | DataFrame.to_odps_table                         |
| DataFrame.reshuffle                 | DataFrame.mf.reshuffle                          |
| DataFrame.right_join                | DataFrame.merge                                 |
| DataFrame.setdiff                   | DataFrame.merge                                 |
| DataFrame.split                     | Not implemented yet                             |
| DataFrame.std_scale                 | Not implemented yet                             |
| DataFrame.sort                      | DataFrame.sort_values                           |
| DataFrame.switch                    | maxframe.dataframe.case_when                    |
| DataFrame.to_kv                     | Not implemented yet                             |
| DataFrame.union                     | maxframe.dataframe.concat                       |
| DatetimeSequenceExpr.date           | Series.dt.date                                  |
| DatetimeSequenceExpr.day            | Series.dt.day                                   |
| DatetimeSequenceExpr.dayofweek      | Series.dt.dayofweek                             |
| DatetimeSequenceExpr.dayofyear      | Series.dt.dayofyear                             |
| DatetimeSequenceExpr.hour           | Series.dt.hour                                  |
| DatetimeSequenceExpr.is_month_end   | Series.dt.is_month_end                          |
| DatetimeSequenceExpr.is_month_start | Series.dt.is_month_start                        |
| DatetimeSequenceExpr.is_year_end    | Series.dt.is_year_end                           |
| DatetimeSequenceExpr.is_year_start  | Series.dt.is_year_start                         |
| DatetimeSequenceExpr.microsecond    | Series.dt.microsecond                           |
| DatetimeSequenceExpr.min            | Series.dt.min                                   |
| DatetimeSequenceExpr.minute         | Series.dt.minute                                |
| DatetimeSequenceExpr.month          | Series.dt.month                                 |
| DatetimeSequenceExpr.second         | Series.dt.second                                |
| DatetimeSequenceExpr.strftime       | Series.dt.strftime                              |
| DatetimeSequenceExpr.unix_timestamp | Not implemented yet                             |
| DatetimeSequenceExpr.week           | Series.dt.week                                  |
| DatetimeSequenceExpr.weekday        | Series.dt.weekday                               |
| DatetimeSequenceExpr.weekofyear     | Series.dt.weekofyear                            |
| DatetimeSequenceExpr.year           | Series.dt.year                                  |
| SequenceExpr.degrees                | np.degrees(Series)                              |
| SequenceExpr.radians                | np.radians(Series)                              |
| SequenceExpr.tolist                 | Series.to_numpy                                 |
| SequenceExpr.to_datetime            | maxframe.dataframe.to_datetime                  |
| SequenceExpr.topk                   | Not implemented yet                             |
| SequenceExpr.trunc                  | np.trunc(Series)                                |
| SequenceExpr.hll_count              | Not implemented yet                             |
| StringSequenceExpr.capitalize       | Series.str.capitalize                           |
| StringSequenceExpr.contains         | Series.str.contains                             |
| StringSequenceExpr.count            | Series.str.count                                |
| StringSequenceExpr.endswith         | Series.str.endswith                             |
| StringSequenceExpr.find             | Series.str.find                                 |
| StringSequenceExpr.len              | Series.str.len                                  |
| StringSequenceExpr.ljust            | Series.str.ljust                                |
| StringSequenceExpr.lower            | Series.str.lower                                |
| StringSequenceExpr.lstrip           | Series.str.lstrip                               |
| StringSequenceExpr.pad              | Series.str.pad                                  |
| StringSequenceExpr.repeat           | Series.str.repeat                               |
| StringSequenceExpr.replace          | Series.str.replace                              |
| StringSequenceExpr.rfind            | Series.str.rfind                                |
| StringSequenceExpr.rjust            | Series.str.rjust                                |
| StringSequenceExpr.rstrip           | Series.str.rstrip                               |
| StringSequenceExpr.slice            | Series.str.slice                                |
| StringSequenceExpr.startswith       | Series.str.startswith                           |
| StringSequenceExpr.strip            | Series.str.strip                                |
| StringSequenceExpr.swapcase         | Series.str.swapcase                             |
| StringSequenceExpr.title            | Series.str.title                                |
| StringSequenceExpr.translate        | Series.str.translate                            |
| StringSequenceExpr.upper            | Series.str.upper                                |
| StringSequenceExpr.zfill            | Series.str.zfill                                |
| StringSequenceExpr.isalnum          | Series.str.isalnum                              |
| StringSequenceExpr.isalpha          | Series.str.isalpha                              |
| StringSequenceExpr.isdigit          | Series.str.isdigit                              |
| StringSequenceExpr.isspace          | Series.str.isspace                              |
| StringSequenceExpr.islower          | Series.str.islower                              |
| StringSequenceExpr.isupper          | Series.str.isupper                              |
| StringSequenceExpr.istitle          | Series.str.istitle                              |
| StringSequenceExpr.isnumeric        | Series.str.isnumeric                            |
| StringSequenceExpr.isdecimal        | Series.str.isdecimal                            |

## Execution

PyODPS DataFrame and MaxFrame both use lazy execution to leverage efficiency
of code optimization. However, the way to invoke these jobs is changed.
