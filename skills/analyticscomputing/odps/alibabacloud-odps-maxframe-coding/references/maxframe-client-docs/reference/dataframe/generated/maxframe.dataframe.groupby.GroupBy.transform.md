# maxframe.dataframe.groupby.GroupBy.transform

#### GroupBy.transform(f, \*args, dtypes=None, dtype=None, name=None, index=None, output_types=None, skip_infer=False, \*\*kwargs)

Call function producing a like-indexed DataFrame on each group and
return a DataFrame having the same indexes as the original object
filled with the transformed values

* **Parameters:**
  * **f** (*function*) – Function to apply to each group.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **\*args** – Positional arguments to pass to func
  * **\*\*kwargs** – Keyword arguments to be passed into func.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`DataFrame.groupby.apply`, `DataFrame.groupby.aggregate`, `DataFrame.transform`

### Notes

Each group is endowed the attribute ‘name’ in case you need to know
which group you are working on.

The current implementation imposes three requirements on f:

* f must return a value that either has the same shape as the input
  subframe or can be broadcast to the shape of the input subframe.
  For example, if f returns a scalar it will be broadcast to have the
  same shape as the input subframe.
* if this is a DataFrame, f must support application column-by-column
  in the subframe. If f also supports application to the entire subframe,
  then a fast path is used starting from the second chunk.
* f must not mutate groups. Mutation is not supported and may
  produce unexpected results.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock grouped object, and the transform call
may fail.

* For DataFrame output, you need to specify a list or a pandas Series
  as `dtypes` of output DataFrame. `index` of output can also be
  specified.
* For Series output, you need to specify `dtype` and `name` of
  output Series.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A' : ['foo', 'bar', 'foo', 'bar',
...                           'foo', 'bar'],
...                    'B' : ['one', 'one', 'two', 'three',
...                           'two', 'two'],
...                    'C' : [1, 5, 5, 2, 5, 5],
...                    'D' : [2.0, 5., 8., 1., 2., 9.]})
>>> grouped = df.groupby('A')
>>> grouped.transform(lambda x: (x - x.mean()) / x.std()).execute()
          C         D
0 -1.154701 -0.577350
1  0.577350  0.000000
2  0.577350  1.154701
3 -1.154701 -1.000000
4  0.577350 -0.577350
5  0.577350  1.000000
```

Broadcast result of the transformation

```pycon
>>> grouped.transform(lambda x: x.max() - x.min()).execute()
   C    D
0  4  6.0
1  3  8.0
2  4  6.0
3  3  8.0
4  4  6.0
5  3  8.0
```
