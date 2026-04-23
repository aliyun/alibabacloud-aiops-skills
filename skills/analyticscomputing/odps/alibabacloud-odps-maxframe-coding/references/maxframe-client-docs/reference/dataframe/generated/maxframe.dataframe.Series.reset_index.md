# maxframe.dataframe.Series.reset_index

#### Series.reset_index(level=None, drop=False, name=<no_default>, inplace=False, default_index_type: ~maxframe.protocol.DefaultIndexType | str = None, \*\*kwargs)

Generate a new DataFrame or Series with the index reset.

This is useful when the index needs to be treated as a column, or
when the index is meaningless and needs to be reset to the default
before another operation.

* **Parameters:**
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *, or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default optional*) – For a Series with a MultiIndex, only remove the specified levels
    from the index. Removes all levels by default.
  * **drop** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Just reset the index, without inserting it as a column in
    the new DataFrame.
  * **name** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *optional*) – The name to use for the column containing the original Series
    values. Uses `self.name` by default. This argument is ignored
    when drop is True.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Modify the Series in place (do not create a new object).
* **Returns:**
  When drop is False (the default), a DataFrame is returned.
  The newly created columns will come first in the DataFrame,
  followed by the original Series values.
  When drop is True, a Series is returned.
  In either case, if `inplace=True`, no value is returned.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.reset_index`](maxframe.dataframe.DataFrame.reset_index.md#maxframe.dataframe.DataFrame.reset_index)
: Analogous function for DataFrame.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3, 4], name='foo',
...               index=md.Index(['a', 'b', 'c', 'd'], name='idx'))
```

Generate a DataFrame with default index.

```pycon
>>> s.reset_index().execute()
  idx  foo
0   a    1
1   b    2
2   c    3
3   d    4
```

To specify the name of the new column use name.

```pycon
>>> s.reset_index(name='values').execute()
  idx  values
0   a       1
1   b       2
2   c       3
3   d       4
```

To generate a new Series with the default set drop to True.

```pycon
>>> s.reset_index(drop=True).execute()
0    1
1    2
2    3
3    4
Name: foo, dtype: int64
```

To update the Series in place, without generating a new one
set inplace to True. Note that it also requires `drop=True`.

```pycon
>>> s.reset_index(inplace=True, drop=True)
>>> s.execute()
0    1
1    2
2    3
3    4
Name: foo, dtype: int64
```

The level parameter is interesting for Series with a multi-level
index.

```pycon
>>> import numpy as np
>>> import pandas as pd
>>> arrays = [np.array(['bar', 'bar', 'baz', 'baz']),
...           np.array(['one', 'two', 'one', 'two'])]
>>> s2 = md.Series(
...     range(4), name='foo',
...     index=pd.MultiIndex.from_arrays(arrays,
...                                     names=['a', 'b']))
```

To remove a specific level from the Index, use level.

```pycon
>>> s2.reset_index(level='a').execute()
       a  foo
b
one  bar    0
two  bar    1
one  baz    2
two  baz    3
```

If level is not set, all levels are removed from the Index.

```pycon
>>> s2.reset_index().execute()
     a    b  foo
0  bar  one    0
1  bar  two    1
2  baz  one    2
3  baz  two    3
```
