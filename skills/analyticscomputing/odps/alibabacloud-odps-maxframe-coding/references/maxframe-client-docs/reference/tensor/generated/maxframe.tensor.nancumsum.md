# maxframe.tensor.nancumsum

### maxframe.tensor.nancumsum(a, axis=None, dtype=None, out=None)

Return the cumulative sum of tensor elements over a given axis treating Not a
Numbers (NaNs) as zero.  The cumulative sum does not change when NaNs are
encountered and leading NaNs are replaced by zeros.

Zeros are returned for slices that are all-NaN or empty.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the cumulative sum is computed. The default
    (None) is to compute the cumsum over the flattened tensor.
  * **dtype** (*dtype* *,* *optional*) – Type of the returned tensor and of the accumulator in which the
    elements are summed.  If dtype is not specified, it defaults
    to the dtype of a, unless a has an integer dtype with a
    precision less than that of the default platform integer.  In
    that case, the default platform integer is used.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must
    have the same shape and buffer length as the expected output
    but the type will be cast if necessary. See doc.ufuncs
    (Section “Output arguments”) for more details.
* **Returns:**
  **nancumsum** – A new tensor holding the result is returned unless out is
  specified, in which it is returned. The result has the same
  size as a, and the same shape as a if axis is not None
  or a is a 1-d tensor.
* **Return type:**
  Tensor.

#### SEE ALSO
[`numpy.cumsum`](https://numpy.org/doc/stable/reference/generated/numpy.cumsum.html#numpy.cumsum)
: Cumulative sum across tensor propagating NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Show which elements are NaN.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.nancumsum(1).execute()
array([1])
>>> mt.nancumsum([1]).execute()
array([1])
>>> mt.nancumsum([1, mt.nan]).execute()
array([ 1.,  1.])
>>> a = mt.array([[1, 2], [3, mt.nan]])
>>> mt.nancumsum(a).execute()
array([ 1.,  3.,  6.,  6.])
>>> mt.nancumsum(a, axis=0).execute()
array([[ 1.,  2.],
       [ 4.,  2.]])
>>> mt.nancumsum(a, axis=1).execute()
array([[ 1.,  3.],
       [ 3.,  3.]])
```
