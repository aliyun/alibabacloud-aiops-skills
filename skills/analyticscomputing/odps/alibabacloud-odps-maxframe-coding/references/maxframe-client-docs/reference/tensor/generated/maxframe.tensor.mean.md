# maxframe.tensor.mean

### maxframe.tensor.mean(a, axis=None, dtype=None, out=None, keepdims=None)

Compute the arithmetic mean along the specified axis.

Returns the average of the array elements.  The average is taken over
the flattened tensor by default, otherwise over the specified axis.
float64 intermediate and return values are used for integer inputs.

* **Parameters:**
  * **a** (*array_like*) – Tensor containing numbers whose mean is desired. If a is not an
    tensor, a conversion is attempted.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which the means are computed. The default is to
    compute the mean of the flattened array.

    If this is a tuple of ints, a mean is performed over multiple axes,
    instead of a single axis or all the axes as before.
  * **dtype** (*data-type* *,* *optional*) – Type to use in computing the mean.  For integer inputs, the default
    is float64; for floating point inputs, it is the same as the
    input dtype.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  The default
    is `None`; if provided, it must have the same shape as the
    expected output, but the type will be cast if necessary.
    See doc.ufuncs for details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input tensor.

    If the default value is passed, then keepdims will not be
    passed through to the mean method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **m** – If out=None, returns a new tensor containing the mean values,
  otherwise a reference to the output array is returned.
* **Return type:**
  Tensor, see dtype parameter above

#### SEE ALSO
[`average`](maxframe.tensor.average.md#maxframe.tensor.average)
: Weighted average

[`std`](maxframe.tensor.std.md#maxframe.tensor.std), [`var`](maxframe.tensor.var.md#maxframe.tensor.var), [`nanmean`](maxframe.tensor.nanmean.md#maxframe.tensor.nanmean), [`nanstd`](maxframe.tensor.nanstd.md#maxframe.tensor.nanstd), [`nanvar`](maxframe.tensor.nanvar.md#maxframe.tensor.nanvar)

### Notes

The arithmetic mean is the sum of the elements along the axis divided
by the number of elements.

Note that for floating-point input, the mean is computed using the
same precision the input has.  Depending on the input data, this can
cause the results to be inaccurate, especially for float32 (see
example below).  Specifying a higher-precision accumulator using the
dtype keyword can alleviate this issue.

By default, float16 results are computed using float32 intermediates
for extra precision.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, 4]])
>>> mt.mean(a).execute()
2.5
>>> mt.mean(a, axis=0).execute()
array([ 2.,  3.])
>>> mt.mean(a, axis=1).execute()
array([ 1.5,  3.5])
```

In single precision, mean can be inaccurate:

```pycon
>>> a = mt.zeros((2, 512*512), dtype=mt.float32)
>>> a[0, :] = 1.0
>>> a[1, :] = 0.1
>>> mt.mean(a).execute()
0.54999924
```

Computing the mean in float64 is more accurate:

```pycon
>>> mt.mean(a, dtype=mt.float64).execute()
0.55000000074505806
```
