# maxframe.dataframe.Series.round

#### Series.round(decimals=0, \*args, \*\*kwargs)

Round each value in a Series to the given number of decimals.

* **Parameters:**
  **decimals** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0*) – Number of decimal places to round to. If decimals is negative,
  it specifies the number of positions to the left of the decimal point.
* **Returns:**
  Rounded values of the Series.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`numpy.around`](https://numpy.org/doc/stable/reference/generated/numpy.around.html#numpy.around)
: Round values of an np.array.

[`DataFrame.round`](maxframe.dataframe.DataFrame.round.md#maxframe.dataframe.DataFrame.round)
: Round values of a DataFrame.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([0.1, 1.3, 2.7])
>>> s.round().execute()
0    0.0
1    1.0
2    3.0
dtype: float64
```
