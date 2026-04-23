# maxframe.dataframe.Series.str.repeat

#### Series.str.repeat(repeats)

Duplicate each string in the Series or Index.

* **Parameters:**
  **repeats** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* [*int*](https://docs.python.org/3/library/functions.html#int)) – Same value for all (int) or different value per (sequence).
* **Returns:**
  Series or Index of repeated string objects specified by
  input parameter repeats.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [pandas.Index](https://pandas.pydata.org/docs/reference/api/pandas.Index.html#pandas.Index)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(['a', 'b', 'c'])
>>> s.execute()
0    a
1    b
2    c
dtype: object
```

Single int repeats string in Series

```pycon
>>> s.str.repeat(repeats=2).execute()
0    aa
1    bb
2    cc
dtype: object
```

Sequence of int repeats corresponding string in Series

```pycon
>>> s.str.repeat(repeats=[1, 2, 3]).execute()
0      a
1     bb
2    ccc
dtype: object
```
