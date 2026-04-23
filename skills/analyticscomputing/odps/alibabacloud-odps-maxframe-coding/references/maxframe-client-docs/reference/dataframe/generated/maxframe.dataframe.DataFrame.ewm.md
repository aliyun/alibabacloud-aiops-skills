# maxframe.dataframe.DataFrame.ewm

#### DataFrame.ewm(com=None, span=None, halflife=None, alpha=None, min_periods=0, adjust=True, ignore_na=False, axis=0)

Provide exponential weighted functions.

* **Parameters:**
  * **com** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Specify decay in terms of center of mass,
    $\alpha = 1 / (1 + com),\text{ for } com \geq 0$.
  * **span** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Specify decay in terms of span,
    $\alpha = 2 / (span + 1),\text{ for } span \geq 1$.
  * **halflife** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Specify decay in terms of half-life,
    $\alpha = 1 - exp(log(0.5) / halflife),\text{for} halflife > 0$.
  * **alpha** ([*float*](https://docs.python.org/3/library/functions.html#float) *,* *optional*) – Specify smoothing factor $\alpha$ directly,
    $0 < \alpha \leq 1$.
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0*) – Minimum number of observations in window required to have a value
    (otherwise result is NA).
  * **adjust** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Divide by decaying adjustment factor in beginning periods to account
    for imbalance in relative weightings
    (viewing EWMA as a moving average).
  * **ignore_na** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Ignore missing values when calculating weights;
    specify True to reproduce pre-0.15.0 behavior.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to use. The value 0 identifies the rows, and 1
    identifies the columns.
* **Returns:**
  A Window sub-classed for the particular operation.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`rolling`](maxframe.dataframe.DataFrame.rolling.md#maxframe.dataframe.DataFrame.rolling)
: Provides rolling window calculations.

[`expanding`](maxframe.dataframe.DataFrame.expanding.md#maxframe.dataframe.DataFrame.expanding)
: Provides expanding transformations.

### Notes

Exactly one of center of mass, span, half-life, and alpha must be provided.

Allowed values and relationship between the parameters are specified in the
parameter descriptions above; see the link at the end of this section for
a detailed explanation.

When adjust is True (default), weighted averages are calculated using
weights (1-alpha)\*\*(n-1), (1-alpha)\*\*(n-2), …, 1-alpha, 1.

When adjust is False, weighted averages are calculated recursively as:

> weighted_average[0] = arg[0];
> weighted_average[i] = (1-alpha)\*weighted_average[i-1] + alpha\*arg[i].

When ignore_na is False (default), weights are based on absolute positions.
For example, the weights of x and y used in calculating the final weighted
average of [x, None, y] are (1-alpha)\*\*2 and 1 (if adjust is True), and
(1-alpha)\*\*2 and alpha (if adjust is False).

When ignore_na is True (reproducing pre-0.15.0 behavior), weights are based
on relative positions. For example, the weights of x and y used in
calculating the final weighted average of [x, None, y] are 1-alpha and 1
(if adjust is True), and 1-alpha and alpha (if adjust is False).

More details can be found at
[https://pandas.pydata.org/pandas-docs/stable/user_guide/computation.html#exponentially-weighted-windows](https://pandas.pydata.org/pandas-docs/stable/user_guide/computation.html#exponentially-weighted-windows)

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
>>> df.ewm(com=0.5).mean().execute()
          B
0  0.000000
1  0.750000
2  1.615385
3  1.615385
4  3.670213
```
