# maxframe.tensor.nansum

### maxframe.tensor.nansum(a, axis=None, dtype=None, out=None, keepdims=None)

Return the sum of array elements over a given axis treating Not a
Numbers (NaNs) as zero.

Zero is returned for slices that are all-NaN or
empty.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose sum is desired. If a is not an
    tensor, a conversion is attempted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the sum is computed. The default is to compute the
    sum of the flattened array.
  * **dtype** (*data-type* *,* *optional*) – The type of the returned tensor and of the accumulator in which the
    elements are summed.  By default, the dtype of a is used.  An
    exception is when a has an integer type with less precision than
    the platform (u)intp. In that case, the default will be either
    (u)int32 or (u)int64 depending on whether the platform is 32 or 64
    bits. For inexact inputs, dtype must be inexact.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  The default
    is `None`. If provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.  See
    doc.ufuncs for details. The casting of NaN to integer can yield
    unexpected results.
  * **keepdims** – If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original a.
* **Returns:**
  **nansum** – A new tensor holding the result is returned unless out is
  specified, in which it is returned. The result has the same
  size as a, and the same shape as a if axis is not None
  or a is a 1-d array.
* **Return type:**
  Tensor.

#### SEE ALSO
`mt.sum`
: Sum across tensor propagating NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Show which elements are NaN.

[`isfinite`](maxframe.tensor.isfinite.md#maxframe.tensor.isfinite)
: Show which elements are not NaN or +/-inf.

### Notes

If both positive and negative infinity are present, the sum will be Not
A Number (NaN).

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.nansum(1).execute()
1
>>> mt.nansum([1]).execute()
1
>>> mt.nansum([1, mt.nan]).execute()
1.0
>>> a = mt.array([[1, 1], [1, mt.nan]])
>>> mt.nansum(a).execute()
3.0
>>> mt.nansum(a, axis=0).execute()
array([ 2.,  1.])
>>> mt.nansum([1, mt.nan, mt.inf]).execute()
inf
>>> mt.nansum([1, mt.nan, mt.NINF]).execute()
-inf
>>> mt.nansum([1, mt.nan, mt.inf, -mt.inf]).execute() # both +/- infinity present
nan
```
