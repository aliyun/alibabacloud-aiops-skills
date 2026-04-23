# maxframe.tensor.all

### maxframe.tensor.all(a, axis=None, out=None, keepdims=None)

Test whether all array elements along a given axis evaluate to True.

* **Parameters:**
  * **a** (*array_like*) – Input tensor or object that can be converted to a tensor.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which a logical AND reduction is performed.
    The default (axis = None) is to perform a logical AND over all
    the dimensions of the input array. axis may be negative, in
    which case it counts from the last to the first axis.

    If this is a tuple of ints, a reduction is performed on multiple
    axes, instead of a single axis or all the axes as before.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.
    It must have the same shape as the expected output and its
    type is preserved (e.g., if `dtype(out)` is float, the result
    will consist of 0.0’s and 1.0’s).  See doc.ufuncs (Section
    “Output arguments”) for more details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input tensor.

    If the default value is passed, then keepdims will not be
    passed through to the all method of sub-classes of
    ndarray, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **all** – A new boolean or tensor is returned unless out is specified,
  in which case a reference to out is returned.
* **Return type:**
  Tensor, [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
`Tensor.all`
: equivalent method

[`any`](maxframe.tensor.any.md#maxframe.tensor.any)
: Test whether any element along a given axis evaluates to True.

### Notes

Not a Number (NaN), positive infinity and negative infinity
evaluate to True because these are not equal to zero.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.all([[True,False],[True,True]]).execute()
False
```

```pycon
>>> mt.all([[True,False],[True,True]], axis=0).execute()
array([ True, False])
```

```pycon
>>> mt.all([-1, 4, 5]).execute()
True
```

```pycon
>>> mt.all([1.0, mt.nan]).execute()
True
```
