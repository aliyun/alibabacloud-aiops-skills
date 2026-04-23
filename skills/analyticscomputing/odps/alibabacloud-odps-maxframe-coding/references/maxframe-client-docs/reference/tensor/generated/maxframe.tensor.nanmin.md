# maxframe.tensor.nanmin

### maxframe.tensor.nanmin(a, axis=None, out=None, keepdims=None)

Return minimum of a tensor or minimum along an axis, ignoring any NaNs.
When all-NaN slices are encountered a `RuntimeWarning` is raised and
Nan is returned for that slice.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose minimum is desired. If a is not an
    tensor, a conversion is attempted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the minimum is computed. The default is to compute
    the minimum of the flattened tensor.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  The default
    is `None`; if provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.  See
    doc.ufuncs for details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original a.

    If the value is anything but the default, then
    keepdims will be passed through to the min method
    of sub-classes of Tensor.  If the sub-classes methods
    does not implement keepdims any exceptions will be raised.
* **Returns:**
  **nanmin** – An tensor with the same shape as a, with the specified axis
  removed.  If a is a 0-d tensor, or if axis is None, a tensor
  scalar is returned.  The same dtype as a is returned.
* **Return type:**
  Tensor

#### SEE ALSO
[`nanmax`](maxframe.tensor.nanmax.md#maxframe.tensor.nanmax)
: The maximum value of an array along a given axis, ignoring any NaNs.

`amin`
: The minimum value of an array along a given axis, propagating any NaNs.

[`fmin`](maxframe.tensor.fmin.md#maxframe.tensor.fmin)
: Element-wise minimum of two arrays, ignoring any NaNs.

[`minimum`](maxframe.tensor.minimum.md#maxframe.tensor.minimum)
: Element-wise minimum of two arrays, propagating any NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Shows which elements are Not a Number (NaN).

[`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)
: Shows which elements are neither NaN nor infinity.

`amax`, [`fmax`](maxframe.tensor.fmax.md#maxframe.tensor.fmax), [`maximum`](maxframe.tensor.maximum.md#maxframe.tensor.maximum)

### Notes

MaxFrame uses the IEEE Standard for Binary Floating-Point for Arithmetic
(IEEE 754). This means that Not a Number is not equivalent to infinity.
Positive infinity is treated as a very large number and negative
infinity is treated as a very small (i.e. negative) number.

If the input has a integer type the function is equivalent to mt.min.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, mt.nan]])
>>> mt.nanmin(a).execute()
1.0
>>> mt.nanmin(a, axis=0).execute()
array([ 1.,  2.])
>>> mt.nanmin(a, axis=1).execute()
array([ 1.,  3.])
```

When positive infinity and negative infinity are present:

```pycon
>>> mt.nanmin([1, 2, mt.nan, mt.inf]).execute()
1.0
>>> mt.nanmin([1, 2, mt.nan, mt.NINF]).execute()
-inf
```
