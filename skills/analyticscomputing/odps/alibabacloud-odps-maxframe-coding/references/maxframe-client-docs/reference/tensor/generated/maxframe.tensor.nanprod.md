# maxframe.tensor.nanprod

### maxframe.tensor.nanprod(a, axis=None, dtype=None, out=None, keepdims=None)

Return the product of array elements over a given axis treating Not a
Numbers (NaNs) as ones.

One is returned for slices that are all-NaN or empty.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose product is desired. If a is not an
    tensor, a conversion is attempted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the product is computed. The default is to compute
    the product of the flattened tensor.
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
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, the axes which are reduced are left in the result as
    dimensions with size one. With this option, the result will
    broadcast correctly against the original arr.
* **Returns:**
  **nanprod** – A new tensor holding the result is returned unless out is
  specified, in which case it is returned.
* **Return type:**
  Tensor

#### SEE ALSO
`mt.prod`
: Product across array propagating NaNs.

[`isnan`](maxframe.tensor.isnan.md#maxframe.tensor.isnan)
: Show which elements are NaN.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.nanprod(1).execute()
1
>>> mt.nanprod([1]).execute()
1
>>> mt.nanprod([1, mt.nan]).execute()
1.0
>>> a = mt.array([[1, 2], [3, mt.nan]])
>>> mt.nanprod(a).execute()
6.0
>>> mt.nanprod(a, axis=0).execute()
array([ 3.,  2.])
```
