# maxframe.dataframe.Series.case_when

#### Series.case_when(caselist)

Replace values where the conditions are True.

* **Parameters:**
  **caselist** (*A list* *of* *tuples* *of* *conditions and expected replacements*) – Takes the form:  `(condition0, replacement0)`,
  `(condition1, replacement1)`, … .
  `condition` should be a 1-D boolean array-like object
  or a callable. If `condition` is a callable,
  it is computed on the Series
  and should return a boolean Series or array.
  The callable must not change the input Series
  (though pandas doesn\`t check it). `replacement` should be a
  1-D array-like object, a scalar or a callable.
  If `replacement` is a callable, it is computed on the Series
  and should return a scalar or Series. The callable
  must not change the input Series.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.mask`](maxframe.dataframe.Series.mask.md#maxframe.dataframe.Series.mask)
: Replace values where the condition is True.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> c = md.Series([6, 7, 8, 9], name='c')
>>> a = md.Series([0, 0, 1, 2])
>>> b = md.Series([0, 3, 4, 5])
```

```pycon
>>> c.case_when(caselist=[(a.gt(0), a),  # condition, replacement
...                       (b.gt(0), b)]).execute()
0    6
1    3
2    1
3    2
Name: c, dtype: int64
```
