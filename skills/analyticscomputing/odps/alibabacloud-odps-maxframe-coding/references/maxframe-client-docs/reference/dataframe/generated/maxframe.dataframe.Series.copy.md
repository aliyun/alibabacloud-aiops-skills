# maxframe.dataframe.Series.copy

#### Series.copy(deep=True)

Make a copy of this object’s indices and data.

When `deep=True` (default), a new object will be created with a
copy of the calling object’s data and indices. Modifications to
the data or indices of the copy will not be reflected in the
original object (see notes below).

When `deep=False`, a new object will be created without copying
the calling object’s data or index (only references to the data
and index are copied). Any changes to the data of the original
will be reflected in the shallow copy (and vice versa).

* **Parameters:**
  **deep** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Make a deep copy, including a copy of the data and the indices.
  With `deep=False` neither the indices nor the data are copied.
* **Returns:**
  **copy** – Object type matches caller.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
