# maxframe.dataframe.Index.to_series

#### Index.to_series(index=None, name=None)

Create a Series with both index and values equal to the index keys.

Useful with map for returning an indexer based on an index.

* **Parameters:**
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *optional*) – Index of resulting Series. If None, defaults to original index.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Dame of resulting Series. If None, defaults to name of original
    index.
* **Returns:**
  The dtype will be based on the type of the Index values.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
