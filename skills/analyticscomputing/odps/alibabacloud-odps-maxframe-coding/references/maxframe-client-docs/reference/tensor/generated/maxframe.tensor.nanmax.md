# maxframe.tensor.nanmax

### maxframe.tensor.nanmax(a, axis=None, out=None, keepdims=None)

Return the maximum of an array or maximum along an axis, ignoring any
NaNs.  When all-NaN slices are encountered a `RuntimeWarning` is
raised and NaN is returned for that slice.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose maximum is desired. If a is not a
    tensor, a conversion is attempted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the maximum is computed. The default is to compute
    the maximum of the flattened tensor.
  * **out** (*ndarray* *,* *optional*) – Alternate output array in which to place the result.  The default
    is `None`; if provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.  See
    doc.ufuncs for details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original a.

    If the value is anything but the default, then
    keepdims will be passed through to the max method
    of sub-classes of Tensor.  If the sub-classes methods
    does not implement keepdims any exceptions will be raised.
* **Returns:**
  **nanmax** – A tensor with the same shape as a, with the specified axis removed.
  If a is a 0-d tensor, or if axis is None, a Tensor scalar is
  returned.  The same dtype as a is returned.
* **Return type:**
  Tensor

#### SEE ALSO
[`nanmin`](maxframe.tensor.nanmin.md#maxframe.tensor.nanmin)
: The minimum value of a tensor along a given axis, ignoring any NaNs.

`amax`
: The maximum value of a tensor along a given axis, propagating any NaNs.

[`fmax`](maxframe.tensor.fmax.md#maxframe.tensor.fmax)
: Element-wise maximum of two tensors, ignoring any NaNs.

[`maximum`](maxframe.tensor.maximum.md#maxframe.tensor.maximum)
: Element-wise maximum of two tensors, propagating any NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Shows which elements are Not a Number (NaN).

[`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)
: Shows which elements are neither NaN nor infinity.

`amin`, [`fmin`](maxframe.tensor.fmin.md#maxframe.tensor.fmin), [`minimum`](maxframe.tensor.minimum.md#maxframe.tensor.minimum)

### Notes

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754). This means that Not a Number is not equivalent to infinity.
Positive infinity is treated as a very large number and negative
infinity is treated as a very small (i.e. negative) number.

If the input has a integer type the function is equivalent to np.max.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, mt.nan]])
>>> mt.nanmax(a).execute()
3.0
>>> mt.nanmax(a, axis=0).execute()
array([ 3.,  2.])
>>> mt.nanmax(a, axis=1).execute()
array([ 2.,  3.])
```

When positive infinity and negative infinity are present:

```pycon
>>> mt.nanmax([1, 2, mt.nan, mt.NINF]).execute()
2.0
>>> mt.nanmax([1, 2, mt.nan, mt.inf]).execute()
inf
```
