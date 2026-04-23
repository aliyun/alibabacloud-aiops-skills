# maxframe.tensor.nanargmin

### maxframe.tensor.nanargmin(a, axis=None, out=None)

Return the indices of the minimum values in the specified axis ignoring
NaNs. For all-NaN slices `ValueError` is raised. Warning: the results
cannot be trusted if a slice contains only NaNs and Infs.

* **Parameters:**
  * **a** (*array_like*) – Input data.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which to operate. By default flattened input is used.
* **Returns:**
  **index_array** – A tensor of indices or a single index value.
* **Return type:**
  Tensor

#### SEE ALSO
[`argmin`](maxframe.tensor.argmin.md#maxframe.tensor.argmin), [`nanargmax`](maxframe.tensor.nanargmax.md#maxframe.tensor.nanargmax)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[mt.nan, 4], [2, 3]])
>>> mt.argmin(a).execute()
0
>>> mt.nanargmin(a).execute()
2
>>> mt.nanargmin(a, axis=0).execute()
array([1, 1])
>>> mt.nanargmin(a, axis=1).execute()
array([1, 0])
```
