# maxframe.dataframe.DataFrame.drop

#### DataFrame.drop(labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise')

Drop specified labels from rows or columns.

Remove rows or columns by specifying label names and corresponding
axis, or by specifying directly index or column names. When using a
multi-index, labels on different levels can be removed by specifying
the level.

* **Parameters:**
  * **labels** (*single label* *or* *list-like*) – Index or column labels to drop.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Whether to drop labels from the index (0 or ‘index’) or
    columns (1 or ‘columns’).
  * **index** (*single label* *or* *list-like*) – Alternative to specifying axis (`labels, axis=0`
    is equivalent to `index=labels`).
  * **columns** (*single label* *or* *list-like*) – Alternative to specifying axis (`labels, axis=1`
    is equivalent to `columns=labels`).
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *level name* *,* *optional*) – For MultiIndex, level from which the labels will be removed.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, do operation inplace and return None.
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'raise'*) – If ‘ignore’, suppress error and only existing labels are
    dropped. Note that errors for missing indices will not raise.
* **Returns:**
  DataFrame without the removed index or column labels.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If any of the labels is not found in the selected axis.

#### SEE ALSO
[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Label-location based indexer for selection by label.

[`DataFrame.dropna`](maxframe.dataframe.DataFrame.dropna.md#maxframe.dataframe.DataFrame.dropna)
: Return DataFrame with labels on given axis omitted where (all or any) data are missing.

[`DataFrame.drop_duplicates`](maxframe.dataframe.DataFrame.drop_duplicates.md#maxframe.dataframe.DataFrame.drop_duplicates)
: Return DataFrame with duplicate rows removed, optionally only considering certain columns.

[`Series.drop`](maxframe.dataframe.Series.drop.md#maxframe.dataframe.Series.drop)
: Return Series with specified index labels removed.

### Examples

```pycon
>>> import numpy as np
>>> import pandas as pd
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(np.arange(12).reshape(3, 4),
...                   columns=['A', 'B', 'C', 'D'])
>>> df.execute()
   A  B   C   D
0  0  1   2   3
1  4  5   6   7
2  8  9  10  11
```

Drop columns

```pycon
>>> df.drop(['B', 'C'], axis=1).execute()
   A   D
0  0   3
1  4   7
2  8  11
```

```pycon
>>> df.drop(columns=['B', 'C']).execute()
   A   D
0  0   3
1  4   7
2  8  11
```

Drop a row by index

```pycon
>>> df.drop([0, 1]).execute()
   A  B   C   D
2  8  9  10  11
```

Drop columns and/or rows of MultiIndex DataFrame

```pycon
>>> midx = pd.MultiIndex(levels=[['lame', 'cow', 'falcon'],
...                              ['speed', 'weight', 'length']],
...                      codes=[[0, 0, 0, 1, 1, 1, 2, 2, 2],
...                             [0, 1, 2, 0, 1, 2, 0, 1, 2]])
>>> df = md.DataFrame(index=midx, columns=['big', 'small'],
...                   data=[[45, 30], [200, 100], [1.5, 1], [30, 20],
...                         [250, 150], [1.5, 0.8], [320, 250],
...                         [1, 0.8], [0.3, 0.2]])
>>> df.execute()
                big     small
lame    speed   45.0    30.0
        weight  200.0   100.0
        length  1.5     1.0
cow     speed   30.0    20.0
        weight  250.0   150.0
        length  1.5     0.8
falcon  speed   320.0   250.0
        weight  1.0     0.8
        length  0.3     0.2
```

```pycon
>>> df.drop(index='cow', columns='small').execute()
                big
lame    speed   45.0
        weight  200.0
        length  1.5
falcon  speed   320.0
        weight  1.0
        length  0.3
```

```pycon
>>> df.drop(index='length', level=1).execute()
                big     small
lame    speed   45.0    30.0
        weight  200.0   100.0
cow     speed   30.0    20.0
        weight  250.0   150.0
falcon  speed   320.0   250.0
        weight  1.0     0.8
```
