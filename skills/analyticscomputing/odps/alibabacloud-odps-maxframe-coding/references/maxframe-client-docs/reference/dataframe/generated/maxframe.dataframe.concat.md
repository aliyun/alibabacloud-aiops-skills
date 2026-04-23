# maxframe.dataframe.concat

### maxframe.dataframe.concat(objs, axis=0, join='outer', ignore_index=False, keys=None, levels=None, names=None, verify_integrity=False, sort=False, copy=True, default_index_type=None)

Concatenate dataframe objects along a particular axis with optional set logic
along the other axes.

Can also add a layer of hierarchical indexing on the concatenation axis,
which may be useful if the labels are the same (or overlapping) on
the passed axis number.

* **Parameters:**
  * **objs** (*a sequence* *or* *mapping* *of* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *or* *DataFrame objects*) – If a mapping is passed, the sorted keys will be used as the keys
    argument, unless it is passed, in which case the values will be
    selected (see below). Any None objects will be dropped silently unless
    they are all None in which case a ValueError will be raised.
  * **axis** ( *{0/'index'* *,* *1/'columns'}* *,* *default 0*) – The axis to concatenate along.
  * **join** ( *{'inner'* *,*  *'outer'}* *,* *default 'outer'*) – How to handle indexes on other axis (or axes).
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, do not use the index values along the concatenation axis. The
    resulting axis will be labeled 0, …, n - 1. This is useful if you are
    concatenating objects where the concatenation axis does not have
    meaningful indexing information. Note the index values on the other
    axes are still respected in the join.
  * **keys** (*sequence* *,* *default None*) – If multiple levels passed, should contain tuples. Construct
    hierarchical index using the passed keys as the outermost level.
  * **levels** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *sequences* *,* *default None*) – Specific levels (unique values) to use for constructing a
    MultiIndex. Otherwise they will be inferred from the keys.
  * **names** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default None*) – Names for the levels in the resulting hierarchical index.
  * **verify_integrity** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Check whether the new concatenated axis contains duplicates. This can
    be very expensive relative to the actual data concatenation.
  * **sort** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Sort non-concatenation axis if it is not already aligned when join
    is ‘outer’.
    This has no effect when `join='inner'`, which already preserves
    the order of the non-concatenation axis.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If False, do not copy data unnecessarily.
* **Returns:**
  When concatenating all `Series` along the index (axis=0), a
  `Series` is returned. When `objs` contains at least one
  `DataFrame`, a `DataFrame` is returned. When concatenating along
  the columns (axis=1), a `DataFrame` is returned.
* **Return type:**
  [object](https://docs.python.org/3/library/functions.html#object), [type](https://docs.python.org/3/library/functions.html#type) of objs

#### SEE ALSO
[`Series.append`](maxframe.dataframe.Series.append.md#maxframe.dataframe.Series.append)
: Concatenate Series.

[`DataFrame.append`](maxframe.dataframe.DataFrame.append.md#maxframe.dataframe.DataFrame.append)
: Concatenate DataFrames.

[`DataFrame.join`](maxframe.dataframe.DataFrame.join.md#maxframe.dataframe.DataFrame.join)
: Join DataFrames using indexes.

[`DataFrame.merge`](maxframe.dataframe.DataFrame.merge.md#maxframe.dataframe.DataFrame.merge)
: Merge DataFrames by indexes or columns.

### Notes

The keys, levels, and names arguments are all optional.

A walkthrough of how this method fits in with other tools for combining
pandas objects can be found [here](https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html).

### Examples

Combine two `Series`.

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series(['a', 'b'])
>>> s2 = md.Series(['c', 'd'])
>>> md.concat([s1, s2]).execute()
0    a
1    b
0    c
1    d
dtype: object
```

Clear the existing index and reset it in the result
by setting the `ignore_index` option to `True`.

```pycon
>>> md.concat([s1, s2], ignore_index=True).execute()
0    a
1    b
2    c
3    d
dtype: object
```

Add a hierarchical index at the outermost level of
the data with the `keys` option.

```pycon
>>> md.concat([s1, s2], keys=['s1', 's2']).execute()
s1  0    a
    1    b
s2  0    c
    1    d
dtype: object
```

Label the index keys you create with the `names` option.

```pycon
>>> md.concat([s1, s2], keys=['s1', 's2'],
...           names=['Series name', 'Row ID']).execute()
Series name  Row ID
s1           0         a
             1         b
s2           0         c
             1         d
dtype: object
```

Combine two `DataFrame` objects with identical columns.

```pycon
>>> df1 = md.DataFrame([['a', 1], ['b', 2]],
...                    columns=['letter', 'number'])
>>> df1.execute()
  letter  number
0      a       1
1      b       2
>>> df2 = md.DataFrame([['c', 3], ['d', 4]],
...                    columns=['letter', 'number'])
>>> df2.execute()
  letter  number
0      c       3
1      d       4
>>> md.concat([df1, df2]).execute()
  letter  number
0      a       1
1      b       2
0      c       3
1      d       4
```

Combine `DataFrame` objects with overlapping columns
and return everything. Columns outside the intersection will
be filled with `NaN` values.

```pycon
>>> df3 = md.DataFrame([['c', 3, 'cat'], ['d', 4, 'dog']],
...                    columns=['letter', 'number', 'animal'])
>>> df3.execute()
  letter  number animal
0      c       3    cat
1      d       4    dog
>>> md.concat([df1, df3], sort=False).execute()
  letter  number animal
0      a       1    NaN
1      b       2    NaN
0      c       3    cat
1      d       4    dog
```

Combine `DataFrame` objects with overlapping columns
and return only those that are shared by passing `inner` to
the `join` keyword argument.

```pycon
>>> md.concat([df1, df3], join="inner").execute()
  letter  number
0      a       1
1      b       2
0      c       3
1      d       4
```

Combine `DataFrame` objects horizontally along the x axis by
passing in `axis=1`.

```pycon
>>> df4 = md.DataFrame([['bird', 'polly'], ['monkey', 'george']],
...                    columns=['animal', 'name'])
>>> md.concat([df1, df4], axis=1).execute()
  letter  number  animal    name
0      a       1    bird   polly
1      b       2  monkey  george
```

Prevent the result from including duplicate index values with the
`verify_integrity` option.

```pycon
>>> df5 = md.DataFrame([1], index=['a'])
>>> df5.execute()
   0
a  1
>>> df6 = md.DataFrame([2], index=['a'])
>>> df6.execute()
   0
a  2
```
