# maxframe.dataframe.Index.drop

#### Index.drop(labels, errors='raise')

Make new Index with passed list of labels deleted.

* **Parameters:**
  * **labels** (*array-like*)
  * **errors** ( *{'ignore'* *,*  *'raise'}* *,* *default 'raise'*) – Note that this argument is kept only for compatibility, and errors
    will not raise even if `errors=='raise'`.
* **Returns:**
  **dropped**
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If not all of the labels are found in the selected axis
