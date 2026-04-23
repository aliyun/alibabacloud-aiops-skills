# maxframe.dataframe.DataFrame.insert

#### DataFrame.insert(loc, column, value, allow_duplicates=False)

Insert column into DataFrame at specified location.

Raises a ValueError if column is already contained in the DataFrame,
unless allow_duplicates is set to True.

* **Parameters:**
  * **loc** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Insertion index. Must verify 0 <= loc <= len(columns).
  * **column** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *number* *, or* *hashable object*) – Label of the inserted column.
  * **value** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *, or* *array-like*)
  * **allow_duplicates** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*)
