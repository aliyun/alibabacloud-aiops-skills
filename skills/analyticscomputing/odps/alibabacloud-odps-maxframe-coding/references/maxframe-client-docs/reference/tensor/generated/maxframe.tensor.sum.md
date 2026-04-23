# maxframe.tensor.sum

### maxframe.tensor.sum(a, axis=None, dtype=None, out=None, keepdims=None)

Sum of tensor elements over a given axis.

* **Parameters:**
  * **a** (*array_like*) – Elements to sum.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which a sum is performed.  The default,
    axis=None, will sum all of the elements of the input tensor.  If
    axis is negative it counts from the last to the first axis.

    If axis is a tuple of ints, a sum is performed on all of the axes
    specified in the tuple instead of a single axis or all the axes as
    before.
  * **dtype** (*dtype* *,* *optional*) – The type of the returned tensor and of the accumulator in which the
    elements are summed.  The dtype of a is used by default unless a
    has an integer dtype of less precision than the default platform
    integer.  In that case, if a is signed then the platform integer
    is used while if a is unsigned then an unsigned integer of the
    same precision as the platform integer is used.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must have
    the same shape as the expected output, but the type of the output
    values will be cast if necessary.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input tensor.

    If the default value is passed, then keepdims will not be
    passed through to the sum method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **sum_along_axis** – An array with the same shape as a, with the specified
  axis removed.   If a is a 0-d tensor, or if axis is None, a scalar
  is returned.  If an output array is specified, a reference to
  out is returned.
* **Return type:**
  Tensor

#### SEE ALSO
`Tensor.sum`
: Equivalent method.

[`cumsum`](maxframe.tensor.cumsum.md#maxframe.tensor.cumsum)
: Cumulative sum of tensor elements.

`trapz`
: Integration of tensor values using the composite trapezoidal rule.

[`mean`](maxframe.tensor.mean.md#maxframe.tensor.mean), [`average`](maxframe.tensor.average.md#maxframe.tensor.average)

### Notes

Arithmetic is modular when using integer types, and no error is
raised on overflow.

The sum of an empty array is the neutral element 0:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.sum([]).execute()
0.0
```

### Examples

```pycon
>>> mt.sum([0.5, 1.5]).execute()
2.0
>>> mt.sum([0.5, 0.7, 0.2, 1.5], dtype=mt.int32).execute()
1
>>> mt.sum([[0, 1], [0, 5]]).execute()
6
>>> mt.sum([[0, 1], [0, 5]], axis=0).execute()
array([0, 6])
>>> mt.sum([[0, 1], [0, 5]], axis=1).execute()
array([1, 5])
```

If the accumulator is too small, overflow occurs:

```pycon
>>> mt.ones(128, dtype=mt.int8).sum(dtype=mt.int8).execute()
-128
```
