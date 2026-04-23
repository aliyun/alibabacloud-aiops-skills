# maxframe.dataframe.DataFrame.reindex

#### DataFrame.reindex(labels=None, , index=None, columns=None, axis=None, method=None, copy=None, level=None, fill_value=None, limit=None, tolerance=None, enable_sparse=False)

Conform Series/DataFrame to new index with optional filling logic.

Places NA/NaN in locations having no value in the previous index. A new object
is produced unless the new index is equivalent to the current one and
`copy=False`.

* **Parameters:**
  * **labels** (*array-like* *,* *optional*) – New labels / index to conform the axis specified by ‘axis’ to.
  * **index** (*array-like* *,* *optional*) – New labels / index to conform to, should be specified using
    keywords. Preferably an Index object to avoid duplicating data.
  * **columns** (*array-like* *,* *optional*) – New labels / index to conform to, should be specified using
    keywords. Preferably an Index object to avoid duplicating data.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Axis to target. Can be either the axis name (‘index’, ‘columns’)
    or number (0, 1).
  * **method** ( *{None* *,*  *'backfill'/'bfill'* *,*  *'pad'/'ffill'* *,*  *'nearest'}*) – 

    Method to use for filling holes in reindexed DataFrame.
    Please note: this is only applicable to DataFrames/Series with a
    monotonically increasing/decreasing index.
    * None (default): don’t fill gaps
    * pad / ffill: Propagate last valid observation forward to next
      valid.
    * backfill / bfill: Use next valid observation to fill gap.
    * nearest: Use nearest valid observations to fill gap.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Return a new object, even if the passed indexes are the same.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *name*) – Broadcast across a level, matching Index values on the
    passed MultiIndex level.
  * **fill_value** (*scalar* *,* *default np.NaN*) – Value to use for missing values. Defaults to NaN, but can be any
    “compatible” value.
  * **limit** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Maximum number of consecutive elements to forward or backward fill.
  * **tolerance** (*optional*) – 

    Maximum distance between original and new labels for inexact
    matches. The values of the index at the matching locations most
    satisfy the equation `abs(index[indexer] - target) <= tolerance`.

    Tolerance may be a scalar value, which applies the same tolerance
    to all values, or list-like, which applies variable tolerance per
    element. List-like includes list, tuple, array, Series, and must be
    the same size as the index and its dtype must exactly match the
    index’s type.
* **Return type:**
  Series/DataFrame with changed index.

#### SEE ALSO
[`DataFrame.set_index`](maxframe.dataframe.DataFrame.set_index.md#maxframe.dataframe.DataFrame.set_index)
: Set row labels.

[`DataFrame.reset_index`](maxframe.dataframe.DataFrame.reset_index.md#maxframe.dataframe.DataFrame.reset_index)
: Remove row labels or move them to new columns.

[`DataFrame.reindex_like`](maxframe.dataframe.DataFrame.reindex_like.md#maxframe.dataframe.DataFrame.reindex_like)
: Change to same indices as other DataFrame.

### Examples

`DataFrame.reindex` supports two calling conventions

* `(index=index_labels, columns=column_labels, ...)`
* `(labels, axis={'index', 'columns'}, ...)`

We *highly* recommend using keyword arguments to clarify your
intent.

Create a dataframe with some fictional data.

```pycon
>>> import maxframe.dataframe as md
>>> index = ['Firefox', 'Chrome', 'Safari', 'IE10', 'Konqueror']
>>> df = md.DataFrame({'http_status': [200, 200, 404, 404, 301],
...                   'response_time': [0.04, 0.02, 0.07, 0.08, 1.0]},
...                   index=index)
>>> df.execute()
           http_status  response_time
Firefox            200           0.04
Chrome             200           0.02
Safari             404           0.07
IE10               404           0.08
Konqueror          301           1.00
```

Create a new index and reindex the dataframe. By default
values in the new index that do not have corresponding
records in the dataframe are assigned `NaN`.

```pycon
>>> new_index = ['Safari', 'Iceweasel', 'Comodo Dragon', 'IE10',
...              'Chrome']
>>> df.reindex(new_index).execute()
               http_status  response_time
Safari               404.0           0.07
Iceweasel              NaN            NaN
Comodo Dragon          NaN            NaN
IE10                 404.0           0.08
Chrome               200.0           0.02
```

We can fill in the missing values by passing a value to
the keyword `fill_value`. Because the index is not monotonically
increasing or decreasing, we cannot use arguments to the keyword
`method` to fill the `NaN` values.

```pycon
>>> df.reindex(new_index, fill_value=0).execute()
               http_status  response_time
Safari                 404           0.07
Iceweasel                0           0.00
Comodo Dragon            0           0.00
IE10                   404           0.08
Chrome                 200           0.02
```

```pycon
>>> df.reindex(new_index, fill_value='missing').execute()
              http_status response_time
Safari                404          0.07
Iceweasel         missing       missing
Comodo Dragon     missing       missing
IE10                  404          0.08
Chrome                200          0.02
```

We can also reindex the columns.

```pycon
>>> df.reindex(columns=['http_status', 'user_agent']).execute()
           http_status  user_agent
Firefox            200         NaN
Chrome             200         NaN
Safari             404         NaN
IE10               404         NaN
Konqueror          301         NaN
```

Or we can use “axis-style” keyword arguments

```pycon
>>> df.reindex(['http_status', 'user_agent'], axis="columns").execute()
           http_status  user_agent
Firefox            200         NaN
Chrome             200         NaN
Safari             404         NaN
IE10               404         NaN
Konqueror          301         NaN
```

To further illustrate the filling functionality in
`reindex`, we will create a dataframe with a
monotonically increasing index (for example, a sequence
of dates).

```pycon
>>> date_index = md.date_range('1/1/2010', periods=6, freq='D')
>>> df2 = md.DataFrame({"prices": [100, 101, np.nan, 100, 89, 88]},
...                    index=date_index)
>>> df2.execute()
            prices
2010-01-01   100.0
2010-01-02   101.0
2010-01-03     NaN
2010-01-04   100.0
2010-01-05    89.0
2010-01-06    88.0
```

Suppose we decide to expand the dataframe to cover a wider
date range.

```pycon
>>> date_index2 = md.date_range('12/29/2009', periods=10, freq='D')
>>> df2.reindex(date_index2).execute()
            prices
2009-12-29     NaN
2009-12-30     NaN
2009-12-31     NaN
2010-01-01   100.0
2010-01-02   101.0
2010-01-03     NaN
2010-01-04   100.0
2010-01-05    89.0
2010-01-06    88.0
2010-01-07     NaN
```

The index entries that did not have a value in the original data frame
(for example, ‘2009-12-29’) are by default filled with `NaN`.
If desired, we can fill in the missing values using one of several
options.

For example, to back-propagate the last valid value to fill the `NaN`
values, pass `bfill` as an argument to the `method` keyword.

```pycon
>>> df2.reindex(date_index2, method='bfill').execute()
            prices
2009-12-29   100.0
2009-12-30   100.0
2009-12-31   100.0
2010-01-01   100.0
2010-01-02   101.0
2010-01-03     NaN
2010-01-04   100.0
2010-01-05    89.0
2010-01-06    88.0
2010-01-07     NaN
```

Please note that the `NaN` value present in the original dataframe
(at index value 2010-01-03) will not be filled by any of the
value propagation schemes. This is because filling while reindexing
does not look at dataframe values, but only compares the original and
desired indexes. If you do want to fill in the `NaN` values present
in the original dataframe, use the `fillna()` method.

See the [user guide](https://pandas.pydata.org/docs/user_guide/basics.html#basics-reindexing) for more.
