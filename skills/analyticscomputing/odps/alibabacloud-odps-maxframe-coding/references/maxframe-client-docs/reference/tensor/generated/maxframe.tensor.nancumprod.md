# maxframe.tensor.nancumprod

### maxframe.tensor.nancumprod(a, axis=None, dtype=None, out=None)

Return the cumulative product of tensor elements over a given axis treating Not a
Numbers (NaNs) as one.  The cumulative product does not change when NaNs are
encountered and leading NaNs are replaced by ones.

Ones are returned for slices that are all-NaN or empty.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the cumulative product is computed.  By default
    the input is flattened.
  * **dtype** (*dtype* *,* *optional*) – Type of the returned tensor, as well as of the accumulator in which
    the elements are multiplied.  If *dtype* is not specified, it
    defaults to the dtype of a, unless a has an integer dtype with
    a precision less than that of the default platform integer.  In
    that case, the default platform integer is used instead.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must
    have the same shape and buffer length as the expected output
    but the type of the resulting values will be cast if necessary.
* **Returns:**
  **nancumprod** – A new array holding the result is returned unless out is
  specified, in which case it is returned.
* **Return type:**
  Tensor

#### SEE ALSO
`mt.cumprod`
: Cumulative product across array propagating NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Show which elements are NaN.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.nancumprod(1).execute()
array([1])
>>> mt.nancumprod([1]).execute()
array([1])
>>> mt.nancumprod([1, mt.nan]).execute()
array([ 1.,  1.])
>>> a = mt.array([[1, 2], [3, mt.nan]])
>>> mt.nancumprod(a).execute()
array([ 1.,  2.,  6.,  6.])
>>> mt.nancumprod(a, axis=0).execute()
array([[ 1.,  2.],
       [ 3.,  2.]])
>>> mt.nancumprod(a, axis=1).execute()
array([[ 1.,  2.],
       [ 3.,  3.]])
```
