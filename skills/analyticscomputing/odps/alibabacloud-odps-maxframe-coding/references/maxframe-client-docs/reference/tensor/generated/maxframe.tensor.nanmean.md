# maxframe.tensor.nanmean

### maxframe.tensor.nanmean(a, axis=None, dtype=None, out=None, keepdims=None)

Compute the arithmetic mean along the specified axis, ignoring NaNs.

Returns the average of the tensor elements.  The average is taken over
the flattened tensor by default, otherwise over the specified axis.
float64 intermediate and return values are used for integer inputs.

For all-NaN slices, NaN is returned and a RuntimeWarning is raised.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose mean is desired. If a is not an
    tensor, a conversion is attempted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the means are computed. The default is to compute
    the mean of the flattened tensor.
  * **dtype** (*data-type* *,* *optional*) – Type to use in computing the mean.  For integer inputs, the default
    is float64; for inexact inputs, it is the same as the input
    dtype.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  The default
    is `None`; if provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.  See
    doc.ufuncs for details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original a.

    If the value is anything but the default, then
    keepdims will be passed through to the mean or sum methods
    of sub-classes of Tensor.  If the sub-classes methods
    does not implement keepdims any exceptions will be raised.
* **Returns:**
  **m** – If out=None, returns a new array containing the mean values,
  otherwise a reference to the output array is returned. Nan is
  returned for slices that contain only NaNs.
* **Return type:**
  Tensor, see dtype parameter above

#### SEE ALSO
[`average`](maxframe.tensor.average.md#maxframe.tensor.average)
: Weighted average

[`mean`](maxframe.tensor.mean.md#maxframe.tensor.mean)
: Arithmetic mean taken while not ignoring NaNs

[`var`](maxframe.tensor.var.md#maxframe.tensor.var), [`nanvar`](maxframe.tensor.nanvar.md#maxframe.tensor.nanvar)

### Notes

The arithmetic mean is the sum of the non-NaN elements along the axis
divided by the number of non-NaN elements.

Note that for floating-point input, the mean is computed using the same
precision the input has.  Depending on the input data, this can cause
the results to be inaccurate, especially for float32.  Specifying a
higher-precision accumulator using the dtype keyword can alleviate
this issue.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, mt.nan], [3, 4]])
>>> mt.nanmean(a).execute()
2.6666666666666665
>>> mt.nanmean(a, axis=0).execute()
array([ 2.,  4.])
>>> mt.nanmean(a, axis=1).execute()
array([ 1.,  3.5])
```
