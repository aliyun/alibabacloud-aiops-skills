# maxframe.dataframe.Index.fillna

#### Index.fillna(value=None, downcast=None)

Fill NA/NaN values with the specified value.

* **Parameters:**
  * **value** (*scalar*) – Scalar value to use to fill holes (e.g. 0).
    This value cannot be a list-likes.
  * **downcast** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *,* *default is None*) – A dict of item->dtype of what to downcast if possible,
    or the string ‘infer’ which will try to downcast to an appropriate
    equal type (e.g. float64 to int64 if possible).
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`DataFrame.fillna`](maxframe.dataframe.DataFrame.fillna.md#maxframe.dataframe.DataFrame.fillna)
: Fill NaN values of a DataFrame.

[`Series.fillna`](maxframe.dataframe.Series.fillna.md#maxframe.dataframe.Series.fillna)
: Fill NaN Values of a Series.
