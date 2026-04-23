# maxframe.dataframe.Series.combine

#### Series.combine(other, func, fill_value=None)

Combine the Series with a Series or scalar according to func.

Combine the Series and other using func to perform elementwise
selection for combined Series.
fill_value is assumed when value is missing at some index
from one of the two objects being combined.

* **Parameters:**
  * **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *or* *scalar*) – The value(s) to be combined with the Series.
  * **func** (*function*) – Function that takes two scalars as inputs and returns an element.
  * **fill_value** (*scalar* *,* *optional*) – The value to assume when an index is missing from
    one Series or the other. The default specifies to use the
    appropriate NaN value for the underlying dtype of the Series.
* **Returns:**
  The result of combining the Series with the other object.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.combine_first`](maxframe.dataframe.Series.combine_first.md#maxframe.dataframe.Series.combine_first)
: Combine Series values, choosing the calling Series’ values first.

### Examples

Consider 2 Datasets `s1` and `s2` containing
highest clocked speeds of different birds.

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series({'falcon': 330.0, 'eagle': 160.0})
>>> s1.execute()
falcon    330.0
eagle     160.0
dtype: float64
>>> s2 = md.Series({'falcon': 345.0, 'eagle': 200.0, 'duck': 30.0})
>>> s2.execute()
falcon    345.0
eagle     200.0
duck       30.0
dtype: float64
```

Now, to combine the two datasets and view the highest speeds
of the birds across the two datasets

```pycon
>>> s1.combine(s2, max).execute()
duck        NaN
eagle     200.0
falcon    345.0
dtype: float64
```

In the previous example, the resulting value for duck is missing,
because the maximum of a NaN and a float is a NaN.
So, in the example, we set `fill_value=0`,
so the maximum value returned will be the value from some dataset.

```pycon
>>> s1.combine(s2, max, fill_value=0).execute()
duck       30.0
eagle     200.0
falcon    345.0
dtype: float64
```
