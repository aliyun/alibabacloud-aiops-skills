# maxframe.dataframe.Index.argmax

#### Index.argmax(axis=0, skipna=True, \*args, \*\*kwargs)

Return int position of the smallest value in the Series.

If the maximum is achieved in multiple locations,
the first row position is returned.

* **Parameters:**
  * **axis** ( *{None}*) – Unused. Parameter needed for compatibility with DataFrame.
  * **skipna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Exclude NA/null values when showing the result.
  * **\*args** – Additional arguments and keywords for compatibility with NumPy.
  * **\*\*kwargs** – Additional arguments and keywords for compatibility with NumPy.
* **Returns:**
  Row position of the maximum value.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`Series.argmin`](maxframe.dataframe.Series.argmin.md#maxframe.dataframe.Series.argmin)
: Return position of the minimum value.

[`Series.argmax`](maxframe.dataframe.Series.argmax.md#maxframe.dataframe.Series.argmax)
: Return position of the maximum value.

[`maxframe.tensor.argmax`](../../tensor/generated/maxframe.tensor.argmax.md#maxframe.tensor.argmax)
: Equivalent method for tensors.

[`Series.idxmax`](maxframe.dataframe.Series.idxmax.md#maxframe.dataframe.Series.idxmax)
: Return index label of the maximum values.

[`Series.idxmin`](maxframe.dataframe.Series.idxmin.md#maxframe.dataframe.Series.idxmin)
: Return index label of the minimum values.

### Examples

Consider dataset containing cereal calories

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series({'Corn Flakes': 100.0, 'Almond Delight': 110.0,
...                'Cinnamon Toast Crunch': 120.0, 'Cocoa Puff': 110.0})
>>> s.execute()
Corn Flakes              100.0
Almond Delight           110.0
Cinnamon Toast Crunch    120.0
Cocoa Puff               110.0
dtype: float64
```

```pycon
>>> s.argmax().execute()
2
>>> s.argmin().execute()
0
```

The maximum cereal calories is the third element and
the minimum cereal calories is the first element,
since series is zero-indexed.
