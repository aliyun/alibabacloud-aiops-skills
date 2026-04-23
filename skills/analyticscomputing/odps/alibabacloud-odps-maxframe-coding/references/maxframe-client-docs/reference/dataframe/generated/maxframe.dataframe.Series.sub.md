# maxframe.dataframe.Series.sub

#### Series.sub(other, level=None, fill_value=None, axis=0)

Return Subtraction of series and other, element-wise (binary operator subtract).

Equivalent to `series - other`, but with support to substitute a fill_value for
missing data in one of the inputs.

* **Parameters:**
  * **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *or* *scalar value*)
  * **fill_value** (*None* *or* *float value* *,* *default None* *(**NaN* *)*) – Fill existing missing (NaN) values, and any new element needed for
    successful Series alignment, with this value before computation.
    If data in both corresponding Series locations is missing
    the result will be missing.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *name*) – Broadcast across a level, matching Index values on the
    passed MultiIndex level.
* **Returns:**
  The result of the operation.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`Series.rsubtract`

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> a = md.Series([1, 1, 1, np.nan], index=['a', 'b', 'c', 'd'])
>>> a.execute()
a    1.0
b    1.0
c    1.0
d    NaN
dtype: float64
```

```pycon
>>> b = md.Series([1, np.nan, 1, np.nan], index=['a', 'b', 'd', 'e'])
>>> b.execute()
a    1.0
b    NaN
d    1.0
e    NaN
dtype: float64
```

```pycon
>>> a.subtract(b, fill_value=0).execute()
a    0.0
b    1.0
c    1.0
d   -1.0
e    NaN
dtype: float64
```
