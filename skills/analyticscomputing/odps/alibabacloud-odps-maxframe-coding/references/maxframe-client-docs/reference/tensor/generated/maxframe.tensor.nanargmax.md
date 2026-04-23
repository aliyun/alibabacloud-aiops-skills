# maxframe.tensor.nanargmax

### maxframe.tensor.nanargmax(a, axis=None, out=None)

Return the indices of the maximum values in the specified axis ignoring
NaNs. For all-NaN slices `ValueError` is raised. Warning: the
results cannot be trusted if a slice contains only NaNs and -Infs.

* **Parameters:**
  * **a** (*array_like*) – Input data.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which to operate.  By default flattened input is used.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  The default
    is `None`; if provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.
    See doc.ufuncs for details.
* **Returns:**
  **index_array** – An tensor of indices or a single index value.
* **Return type:**
  Tensor

#### SEE ALSO
[`argmax`](maxframe.tensor.argmax.md#maxframe.tensor.argmax), [`nanargmin`](maxframe.tensor.nanargmin.md#maxframe.tensor.nanargmin)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[mt.nan, 4], [2, 3]])
>>> mt.argmax(a).execute()
0
>>> mt.nanargmax(a).execute()
1
>>> mt.nanargmax(a, axis=0).execute()
array([1, 0])
>>> mt.nanargmax(a, axis=1).execute()
array([1, 1])
```
