# maxframe.dataframe.Series.explode

#### Series.explode(ignore_index=False, default_index_type=None)

Transform each element of a list-like to a row.

* **Parameters:**
  **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting index will be labeled 0, 1, …, n - 1.
* **Returns:**
  Exploded lists to rows; index will be duplicated for these rows.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`Series.str.split`
: Split string values on specified separator.

[`Series.unstack`](maxframe.dataframe.Series.unstack.md#maxframe.dataframe.Series.unstack)
: Unstack, a.k.a. pivot, Series with MultiIndex to produce DataFrame.

[`DataFrame.melt`](maxframe.dataframe.DataFrame.melt.md#maxframe.dataframe.DataFrame.melt)
: Unpivot a DataFrame from wide format to long format.

`DataFrame.explode`
: Explode a DataFrame from list-like columns to long format.

### Notes

This routine will explode list-likes including lists, tuples,
Series, and np.ndarray. The result dtype of the subset rows will
be object. Scalars will be returned unchanged. Empty list-likes will
result in a np.nan for that row.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([[1, 2, 3], 'foo', [], [3, 4]])
>>> s.execute()
0    [1, 2, 3]
1          foo
2           []
3       [3, 4]
dtype: object
```

```pycon
>>> s.explode().execute()
0      1
0      2
0      3
1    foo
2    NaN
3      3
3      4
dtype: object
```
