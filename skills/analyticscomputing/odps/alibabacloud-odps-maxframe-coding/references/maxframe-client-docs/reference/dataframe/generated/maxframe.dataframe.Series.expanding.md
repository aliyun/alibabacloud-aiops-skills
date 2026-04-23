# maxframe.dataframe.Series.expanding

#### Series.expanding(min_periods=1, shift=0, reverse_range=False)

Provide expanding transformations.

* **Parameters:**
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 1*)
  * **value** (*Minimum number* *of* *observations in window required to have a*)
  * **NA****)****.** ( *(**otherwise result is*)
  * **center** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*)
  * **window.** (*Set the labels at the center* *of* *the*)
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 0*)
* **Return type:**
  a Window sub-classed for the particular operation

#### SEE ALSO
[`rolling`](maxframe.dataframe.Series.rolling.md#maxframe.dataframe.Series.rolling)
: Provides rolling window calculations.

[`ewm`](maxframe.dataframe.Series.ewm.md#maxframe.dataframe.Series.ewm)
: Provides exponential weighted functions.

### Notes

By default, the result is set to the right edge of the window. This can be
changed to the center of the window by setting `center=True`.

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'B': [0, 1, 2, np.nan, 4]})
>>> df.execute()
     B
0  0.0
1  1.0
2  2.0
3  NaN
4  4.0
>>> df.expanding(2).sum().execute()
     B
0  NaN
1  1.0
2  3.0
3  3.0
4  7.0
```
