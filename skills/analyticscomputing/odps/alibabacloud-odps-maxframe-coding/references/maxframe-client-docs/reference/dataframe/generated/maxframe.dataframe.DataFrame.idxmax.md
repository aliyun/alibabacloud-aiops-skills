# maxframe.dataframe.DataFrame.idxmax

#### DataFrame.idxmax(axis=0, skipna=True)

Return index of first occurrence of maximum over requested axis.

NA/null values are excluded.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis to use. 0 or ‘index’ for row-wise, 1 or ‘columns’ for column-wise.
  * **skipna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Exclude NA/null values. If an entire row/column is NA, the result
    will be NA.
* **Returns:**
  Indexes of maxima along the specified axis.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – 
  * If the row/column is empty

#### SEE ALSO
[`Series.idxmax`](maxframe.dataframe.Series.idxmax.md#maxframe.dataframe.Series.idxmax)
: Return index of the maximum element.

### Notes

This method is the DataFrame version of `ndarray.argmax`.

### Examples

Consider a dataset containing food consumption in Argentina.

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'consumption': [10.51, 103.11, 55.48],
...                    'co2_emissions': [37.2, 19.66, 1712]},
...                    index=['Pork', 'Wheat Products', 'Beef'])
```

```pycon
>>> df.execute()
                consumption  co2_emissions
Pork                  10.51         37.20
Wheat Products       103.11         19.66
Beef                  55.48       1712.00
```

By default, it returns the index for the maximum value in each column.

```pycon
>>> df.idxmax().execute()
consumption     Wheat Products
co2_emissions             Beef
dtype: object
```

To return the index for the maximum value in each row, use `axis="columns"`.

```pycon
>>> df.idxmax(axis="columns").execute()
Pork              co2_emissions
Wheat Products     consumption
Beef              co2_emissions
dtype: object
```
