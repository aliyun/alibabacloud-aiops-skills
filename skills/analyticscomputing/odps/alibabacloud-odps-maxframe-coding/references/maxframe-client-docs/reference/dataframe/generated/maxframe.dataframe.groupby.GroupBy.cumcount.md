# maxframe.dataframe.groupby.GroupBy.cumcount

#### GroupBy.cumcount(ascending: [bool](https://docs.python.org/3/library/functions.html#bool) = True)

Number each item in each group from 0 to the length of that group - 1.

Essentially this is equivalent to

```python
self.apply(lambda x: pd.Series(np.arange(len(x)), x.index))
```

* **Parameters:**
  **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If False, number in reverse, from length of group - 1 to 0.
* **Returns:**
  Sequence number of each element within each group.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`ngroup`
: Number the groups themselves.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([['a'], ['a'], ['a'], ['b'], ['b'], ['a']],
...                   columns=['A'])
>>> df.execute()
   A
0  a
1  a
2  a
3  b
4  b
5  a
>>> df.groupby('A').cumcount().execute()
0    0
1    1
2    2
3    0
4    1
5    3
dtype: int64
>>> df.groupby('A').cumcount(ascending=False).execute()
0    3
1    2
2    1
3    1
4    0
5    0
dtype: int64
```
