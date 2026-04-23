# maxframe.dataframe.groupby.GroupBy.cumsum

#### GroupBy.cumsum()

Cumulative sum for each group.

* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`Series.groupby`
: Apply a function groupby to a Series.

`DataFrame.groupby`
: Apply a function groupby to each row or column of a DataFrame.

### Examples

For SeriesGroupBy:

```pycon
>>> import maxframe.dataframe as md
>>> lst = ['a', 'a', 'b']
>>> ser = md.Series([6, 2, 0], index=lst)
>>> ser.execute()
a    6
a    2
b    0
dtype: int64
>>> ser.groupby(level=0).cumsum().execute()
a    6
a    8
b    0
```

For DataFrameGroupBy:

```pycon
>>> data = [[1, 8, 2], [1, 2, 5], [2, 6, 9]]
>>> df = md.DataFrame(data, columns=["a", "b", "c"],
...                   index=["fox", "gorilla", "lion"])
>>> df.execute()
          a   b   c
fox       1   8   2
gorilla   1   2   5
lion      2   6   9
>>> df.groupby("a").groups.execute()
{1: ['fox', 'gorilla'], 2: ['lion']}
>>> df.groupby("a").cumsum().execute()
          b  c
fox       8  2
gorilla  10  7
lion      6  9
```
