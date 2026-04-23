# maxframe.tensor.cumsum

### maxframe.tensor.cumsum(a, axis=None, dtype=None, out=None)

Return the cumulative sum of the elements along a given axis.

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
  **cumsum_along_axis** – A new tensor holding the result is returned unless out is
  specified, in which case a reference to out is returned. The
  result has the same size as a, and the same shape as a if
  axis is not None or a is a 1-d tensor.
* **Return type:**
  Tensor.

#### SEE ALSO
[`sum`](maxframe.tensor.sum.md#maxframe.tensor.sum)
: Sum tensor elements.

`trapz`
: Integration of tensor values using the composite trapezoidal rule.

[`diff`](maxframe.tensor.diff.md#maxframe.tensor.diff)
: Calculate the n-th discrete difference along given axis.

### Notes

Arithmetic is modular when using integer types, and no error is
raised on overflow.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1,2,3], [4,5,6]])
>>> a.execute()
array([[1, 2, 3],
       [4, 5, 6]])
>>> mt.cumsum(a).execute()
array([ 1,  3,  6, 10, 15, 21])
>>> mt.cumsum(a, dtype=float).execute()     # specifies type of output value(s)
array([  1.,   3.,   6.,  10.,  15.,  21.])
```

```pycon
>>> mt.cumsum(a,axis=0).execute()      # sum over rows for each of the 3 columns
array([[1, 2, 3],
       [5, 7, 9]])
>>> mt.cumsum(a,axis=1).execute()      # sum over columns for each of the 2 rows
array([[ 1,  3,  6],
       [ 4,  9, 15]])
```
