# maxframe.tensor.std

### maxframe.tensor.std(a, axis=None, dtype=None, out=None, ddof=0, keepdims=None)

Compute the standard deviation along the specified axis.

Returns the standard deviation, a measure of the spread of a distribution,
of the tensor elements. The standard deviation is computed for the
flattened tensor by default, otherwise over the specified axis.

* **Parameters:**
  * **a** (*array_like*) – Calculate the standard deviation of these values.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which the standard deviation is computed. The
    default is to compute the standard deviation of the flattened tensor.

    If this is a tuple of ints, a standard deviation is performed over
    multiple axes, instead of a single axis or all the axes as before.
  * **dtype** (*dtype* *,* *optional*) – Type to use in computing the standard deviation. For tensors of
    integer type the default is float64, for tensors of float types it is
    the same as the array type.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must have
    the same shape as the expected output but the type (of the calculated
    values) will be cast if necessary.
  * **ddof** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Means Delta Degrees of Freedom.  The divisor used in calculations
    is `N - ddof`, where `N` represents the number of elements.
    By default ddof is zero.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input tensor.

    If the default value is passed, then keepdims will not be
    passed through to the std method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **standard_deviation** – If out is None, return a new tensor containing the standard deviation,
  otherwise return a reference to the output array.
* **Return type:**
  Tensor, see dtype parameter above.

#### SEE ALSO
[`var`](maxframe.tensor.var.md#maxframe.tensor.var), [`mean`](maxframe.tensor.mean.md#maxframe.tensor.mean), [`nanmean`](maxframe.tensor.nanmean.md#maxframe.tensor.nanmean), [`nanstd`](maxframe.tensor.nanstd.md#maxframe.tensor.nanstd), [`nanvar`](maxframe.tensor.nanvar.md#maxframe.tensor.nanvar)

### Notes

The standard deviation is the square root of the average of the squared
deviations from the mean, i.e., `std = sqrt(mean(abs(x - x.mean())**2))`.

The average squared deviation is normally calculated as
`x.sum() / N`, where `N = len(x)`.  If, however, ddof is specified,
the divisor `N - ddof` is used instead. In standard statistical
practice, `ddof=1` provides an unbiased estimator of the variance
of the infinite population. `ddof=0` provides a maximum likelihood
estimate of the variance for normally distributed variables. The
standard deviation computed in this function is the square root of
the estimated variance, so even with `ddof=1`, it will not be an
unbiased estimate of the standard deviation per se.

Note that, for complex numbers, std takes the absolute
value before squaring, so that the result is always real and nonnegative.

For floating-point input, the *std* is computed using the same
precision the input has. Depending on the input data, this can cause
the results to be inaccurate, especially for float32 (see example below).
Specifying a higher-accuracy accumulator using the dtype keyword can
alleviate this issue.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, 4]])
>>> mt.std(a).execute()
1.1180339887498949
>>> mt.std(a, axis=0).execute()
array([ 1.,  1.])
>>> mt.std(a, axis=1).execute()
array([ 0.5,  0.5])
```

In single precision, std() can be inaccurate:

```pycon
>>> a = mt.zeros((2, 512*512), dtype=mt.float32)
>>> a[0, :] = 1.0
>>> a[1, :] = 0.1
>>> mt.std(a).execute()
0.45000005
```

Computing the standard deviation in float64 is more accurate:

```pycon
>>> mt.std(a, dtype=mt.float64).execute()
0.44999999925494177
```
