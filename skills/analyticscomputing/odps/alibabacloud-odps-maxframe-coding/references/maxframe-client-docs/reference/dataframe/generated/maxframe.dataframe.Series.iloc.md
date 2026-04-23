# maxframe.dataframe.Series.iloc

#### *property* Series.iloc

Purely integer-location based indexing for selection by position.

`.iloc[]` is primarily integer position based (from `0` to
`length-1` of the axis), but may also be used with a boolean
array.

Allowed inputs are:

- An integer, e.g. `5`.
- A list or array of integers, e.g. `[4, 3, 0]`.
- A slice object with ints, e.g. `1:7`.
- A boolean array.
- A `callable` function with one argument (the calling Series or
  DataFrame) and that returns valid output for indexing (one of the above).
  This is useful in method chains, when you don’t have a reference to the
  calling object, but would like to base your selection on some value.

`.iloc` will raise `IndexError` if a requested indexer is
out-of-bounds, except *slice* indexers which allow out-of-bounds
indexing (this conforms with python/numpy *slice* semantics).

See more at [Selection by Position](https://pandas.pydata.org/docs/user_guide/indexing.html#indexing-integer).

#### SEE ALSO
[`DataFrame.iat`](maxframe.dataframe.DataFrame.iat.md#maxframe.dataframe.DataFrame.iat)
: Fast integer location scalar accessor.

[`DataFrame.loc`](maxframe.dataframe.DataFrame.loc.md#maxframe.dataframe.DataFrame.loc)
: Purely label-location based indexer for selection by label.

[`Series.iloc`](#maxframe.dataframe.Series.iloc)
: Purely integer-location based indexing for selection by position.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> mydict = [{'a': 1, 'b': 2, 'c': 3, 'd': 4},
...           {'a': 100, 'b': 200, 'c': 300, 'd': 400},
...           {'a': 1000, 'b': 2000, 'c': 3000, 'd': 4000 }]
>>> df = md.DataFrame(mydict)
>>> df.execute()
      a     b     c     d
0     1     2     3     4
1   100   200   300   400
2  1000  2000  3000  4000
```

**Indexing just the rows**

With a scalar integer.

```pycon
>>> type(df.iloc[0]).execute()
<class 'pandas.core.series.Series'>
>>> df.iloc[0].execute()
a    1
b    2
c    3
d    4
Name: 0, dtype: int64
```

With a list of integers.

```pycon
>>> df.iloc[[0]].execute()
   a  b  c  d
0  1  2  3  4
>>> type(df.iloc[[0]]).execute()
<class 'pandas.core.frame.DataFrame'>
```

```pycon
>>> df.iloc[[0, 1]].execute()
     a    b    c    d
0    1    2    3    4
1  100  200  300  400
```

With a slice object.

```pycon
>>> df.iloc[:3].execute()
      a     b     c     d
0     1     2     3     4
1   100   200   300   400
2  1000  2000  3000  4000
```

With a boolean mask the same length as the index.

```pycon
>>> df.iloc[[True, False, True]].execute()
      a     b     c     d
0     1     2     3     4
2  1000  2000  3000  4000
```

With a callable, useful in method chains. The x passed
to the `lambda` is the DataFrame being sliced. This selects
the rows whose index label even.

```pycon
>>> df.iloc[lambda x: x.index % 2 == 0].execute()
      a     b     c     d
0     1     2     3     4
2  1000  2000  3000  4000
```

**Indexing both axes**

You can mix the indexer types for the index and columns. Use `:` to
select the entire axis.

With scalar integers.

```pycon
>>> df.iloc[0, 1].execute()
2
```

With lists of integers.

```pycon
>>> df.iloc[[0, 2], [1, 3]].execute()
      b     d
0     2     4
2  2000  4000
```

With slice objects.

```pycon
>>> df.iloc[1:3, 0:3].execute()
      a     b     c
1   100   200   300
2  1000  2000  3000
```

With a boolean array whose length matches the columns.

```pycon
>>> df.iloc[:, [True, False, True, False]].execute()
      a     c
0     1     3
1   100   300
2  1000  3000
```

With a callable function that expects the Series or DataFrame.

```pycon
>>> df.iloc[:, lambda df: [0, 2]].execute()
      a     c
0     1     3
1   100   300
2  1000  3000
```
