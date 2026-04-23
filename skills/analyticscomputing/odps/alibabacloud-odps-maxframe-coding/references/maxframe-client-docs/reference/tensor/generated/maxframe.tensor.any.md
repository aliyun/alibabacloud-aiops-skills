# maxframe.tensor.any

### maxframe.tensor.any(a, axis=None, out=None, keepdims=None)

Test whether any tensor element along a given axis evaluates to True.

Returns single boolean unless axis is not `None`

* **Parameters:**
  * **a** (*array_like*) – Input tensor or object that can be converted to an array.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – 

    Axis or axes along which a logical OR reduction is performed.
    The default (axis = None) is to perform a logical OR over all
    the dimensions of the input array. axis may be negative, in
    which case it counts from the last to the first axis.

    If this is a tuple of ints, a reduction is performed on multiple
    axes, instead of a single axis or all the axes as before.
  * **out** (*Tensor* *,* *optional*) – Alternate output tensor in which to place the result.  It must have
    the same shape as the expected output and its type is preserved
    (e.g., if it is of type float, then it will remain so, returning
    1.0 for True and 0.0 for False, regardless of the type of a).
    See doc.ufuncs (Section “Output arguments”) for details.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input tensor.

    If the default value is passed, then keepdims will not be
    passed through to the any method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-classes sum method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **any** – A new boolean or Tensor is returned unless out is specified,
  in which case a reference to out is returned.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool) or Tensor

#### SEE ALSO
`Tensor.any`
: equivalent method

[`all`](maxframe.tensor.all.md#maxframe.tensor.all)
: Test whether all elements along a given axis evaluate to True.

### Notes

Not a Number (NaN), positive infinity and negative infinity evaluate
to True because these are not equal to zero.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.any([[True, False], [True, True]]).execute()
True
```

```pycon
>>> mt.any([[True, False], [False, False]], axis=0).execute()
array([ True, False])
```

```pycon
>>> mt.any([-1, 0, 5]).execute()
True
```

```pycon
>>> mt.any(mt.nan).execute()
True
```
