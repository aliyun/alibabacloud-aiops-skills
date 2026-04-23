# maxframe.dataframe.Index.get_level_values

#### Index.get_level_values(level)

Return vector of label values for requested level.

Length of returned vector is equal to the length of the index.

* **Parameters:**
  **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – `level` is either the integer position of the level in the
  MultiIndex, or the name of the level.
* **Returns:**
  **values** – Values is a level of this MultiIndex converted to
  a single [`Index`](maxframe.dataframe.Index.md#maxframe.dataframe.Index) (or subclass thereof).
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

### Examples

Create a MultiIndex:

```pycon
>>> import maxframe.dataframe as md
>>> import pandas as pd
>>> mi = md.Index(pd.MultiIndex.from_arrays((list('abc'), list('def')), names=['level_1', 'level_2']))
```

Get level values by supplying level as either integer or name:

```pycon
>>> mi.get_level_values(0).execute()
Index(['a', 'b', 'c'], dtype='object', name='level_1')
>>> mi.get_level_values('level_2').execute()
Index(['d', 'e', 'f'], dtype='object', name='level_2')
```
