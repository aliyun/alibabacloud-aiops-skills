# maxframe.dataframe.Series.drop

#### Series.drop(labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise')

Return Series with specified index labels removed.

Remove elements of a Series based on specifying the index labels.
When using a multi-index, labels on different levels can be removed
by specifying the level.

* **Parameters:**
  * **labels** (*single label* *or* *list-like*) – Index labels to drop.
  * **axis** (*0* *,* *default 0*) – Redundant for application on Series.
  * **index** (*single label* *or* *list-like*) – 

    Redundant for application on Series, but ‘index’ can be used instead
    of ‘labels’.

    #### Versionadded
    Added in version 0.21.0.
  * **columns** (*single label* *or* *list-like*) – 

    No change is made to the Series; use ‘index’ or ‘labels’ instead.

    #### Versionadded
    Added in version 0.21.0.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *level name* *,* *optional*) – For MultiIndex, level for which the labels will be removed.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, do operation inplace and return None.
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'raise'*) – Note that this argument is kept only for compatibility, and errors
    will not raise even if `errors=='raise'`.
* **Returns:**
  Series with specified index labels removed.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If none of the labels are found in the index.

#### SEE ALSO
[`Series.reindex`](maxframe.dataframe.Series.reindex.md#maxframe.dataframe.Series.reindex)
: Return only specified index labels of Series.

[`Series.dropna`](maxframe.dataframe.Series.dropna.md#maxframe.dataframe.Series.dropna)
: Return series without null values.

[`Series.drop_duplicates`](maxframe.dataframe.Series.drop_duplicates.md#maxframe.dataframe.Series.drop_duplicates)
: Return Series with duplicate values removed.

[`DataFrame.drop`](maxframe.dataframe.DataFrame.drop.md#maxframe.dataframe.DataFrame.drop)
: Drop specified labels from rows or columns.

### Examples

```pycon
>>> import numpy as np
>>> import pandas as pd
>>> import maxframe.dataframe as md
>>> s = md.Series(data=np.arange(3), index=['A', 'B', 'C'])
>>> s.execute()
A  0
B  1
C  2
dtype: int64
```

Drop labels B en C

```pycon
>>> s.drop(labels=['B', 'C']).execute()
A  0
dtype: int64
```

Drop 2nd level label in MultiIndex Series

```pycon
>>> midx = pd.MultiIndex(levels=[['lame', 'cow', 'falcon'],
...                              ['speed', 'weight', 'length']],
...                      codes=[[0, 0, 0, 1, 1, 1, 2, 2, 2],
...                             [0, 1, 2, 0, 1, 2, 0, 1, 2]])
>>> s = md.Series([45, 200, 1.2, 30, 250, 1.5, 320, 1, 0.3],
...               index=midx)
>>> s.execute()
lame    speed      45.0
        weight    200.0
        length      1.2
cow     speed      30.0
        weight    250.0
        length      1.5
falcon  speed     320.0
        weight      1.0
        length      0.3
dtype: float64
```

```pycon
>>> s.drop(labels='weight', level=1).execute()
lame    speed      45.0
        length      1.2
cow     speed      30.0
        length      1.5
falcon  speed     320.0
        length      0.3
dtype: float64
```
