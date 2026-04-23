# maxframe.tensor.nanstd

### maxframe.tensor.nanstd(a, axis=None, dtype=None, out=None, ddof=0, keepdims=None)

Compute the standard deviation along the specified axis, while
ignoring NaNs.

Returns the standard deviation, a measure of the spread of a
distribution, of the non-NaN tensor elements. The standard deviation is
computed for the flattened tensor by default, otherwise over the
specified axis.

For all-NaN slices or slices with zero degrees of freedom, NaN is
returned and a RuntimeWarning is raised.

* **Parameters:**
  * **a** (*array_like*) – Calculate the standard deviation of the non-NaN values.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the standard deviation is computed. The default is
    to compute the standard deviation of the flattened tensor.
  * **dtype** (*dtype* *,* *optional*) – Type to use in computing the standard deviation. For tensors of
    integer type the default is float64, for tensors of float types it
    is the same as the tensor type.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must have
    the same shape as the expected output but the type (of the
    calculated values) will be cast if necessary.
  * **ddof** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Means Delta Degrees of Freedom.  The divisor used in calculations
    is `N - ddof`, where `N` represents the number of non-NaN
    elements.  By default ddof is zero.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original a.

    If this value is anything but the default it is passed through
    as-is to the relevant functions of the sub-classes.  If these
    functions do not have a keepdims kwarg, a RuntimeError will
    be raised.
* **Returns:**
  **standard_deviation** – If out is None, return a new array containing the standard
  deviation, otherwise return a reference to the output tensor. If
  ddof is >= the number of non-NaN elements in a slice or the slice
  contains only NaNs, then the result for that slice is NaN.
* **Return type:**
  ndarray, see dtype parameter above.

#### SEE ALSO
[`var`](maxframe.tensor.var.md#maxframe.tensor.var), [`mean`](maxframe.tensor.mean.md#maxframe.tensor.mean), [`std`](maxframe.tensor.std.md#maxframe.tensor.std), [`nanvar`](maxframe.tensor.nanvar.md#maxframe.tensor.nanvar), [`nanmean`](maxframe.tensor.nanmean.md#maxframe.tensor.nanmean)

### Notes

The standard deviation is the square root of the average of the squared
deviations from the mean: `std = sqrt(mean(abs(x - x.mean())**2))`.

The average squared deviation is normally calculated as
`x.sum() / N`, where `N = len(x)`.  If, however, ddof is
specified, the divisor `N - ddof` is used instead. In standard
statistical practice, `ddof=1` provides an unbiased estimator of the
variance of the infinite population. `ddof=0` provides a maximum
likelihood estimate of the variance for normally distributed variables.
The standard deviation computed in this function is the square root of
the estimated variance, so even with `ddof=1`, it will not be an
unbiased estimate of the standard deviation per se.

Note that, for complex numbers, std takes the absolute value before
squaring, so that the result is always real and nonnegative.

For floating-point input, the *std* is computed using the same
precision the input has. Depending on the input data, this can cause
the results to be inaccurate, especially for float32 (see example
below).  Specifying a higher-accuracy accumulator using the dtype
keyword can alleviate this issue.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, mt.nan], [3, 4]])
>>> mt.nanstd(a).execute()
1.247219128924647
>>> mt.nanstd(a, axis=0).execute()
array([ 1.,  0.])
>>> mt.nanstd(a, axis=1).execute()
array([ 0.,  0.5])
```
