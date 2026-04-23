# maxframe.tensor.isin

### maxframe.tensor.isin(element: TileableType | [ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray), test_elements: TileableType | [ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray) | [list](https://docs.python.org/3/library/stdtypes.html#list), assume_unique: [bool](https://docs.python.org/3/library/functions.html#bool) = False, invert: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Calculates element in test_elements, broadcasting over element only.
Returns a boolean array of the same shape as element that is True
where an element of element is in test_elements and False otherwise.

* **Parameters:**
  * **element** (*array_like*) – Input tensor.
  * **test_elements** (*array_like*) – The values against which to test each value of element.
    This argument is flattened if it is a tensor or array_like.
    See notes for behavior with non-array-like parameters.
  * **assume_unique** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, the input tensors are both assumed to be unique, which
    can speed up the calculation.  Default is False.
  * **invert** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, the values in the returned tensor are inverted, as if
    calculating element not in test_elements. Default is False.
    `mt.isin(a, b, invert=True)` is equivalent to (but faster
    than) `mt.invert(mt.isin(a, b))`.
* **Returns:**
  **isin** – Has the same shape as element. The values element[isin]
  are in test_elements.
* **Return type:**
  Tensor, [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`in1d`](maxframe.tensor.in1d.md#maxframe.tensor.in1d)
: Flattened version of this function.

### Notes

isin is an element-wise function version of the python keyword in.
`isin(a, b)` is roughly equivalent to
`mt.array([item in b for item in a])` if a and b are 1-D sequences.

element and test_elements are converted to tensors if they are not
already. If test_elements is a set (or other non-sequence collection)
it will be converted to an object tensor with one element, rather than a
tensor of the values contained in test_elements. This is a consequence
of the tensor constructor’s way of handling non-sequence collections.
Converting the set to a list usually gives the desired behavior.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> element = 2*mt.arange(4).reshape((2, 2))
>>> element.execute()
array([[0, 2],
       [4, 6]])
>>> test_elements = [1, 2, 4, 8]
>>> mask = mt.isin(element, test_elements)
>>> mask.execute()
array([[ False,  True],
       [ True,  False]])
>>> element[mask].execute()
array([2, 4])
>>> mask = mt.isin(element, test_elements, invert=True)
>>> mask.execute()
array([[ True, False],
       [ False, True]])
>>> element[mask]
array([0, 6])
```

Because of how array handles sets, the following does not
work as expected:

```pycon
>>> test_set = {1, 2, 4, 8}
>>> mt.isin(element, test_set).execute()
array([[ False, False],
       [ False, False]])
```

Casting the set to a list gives the expected result:

```pycon
>>> mt.isin(element, list(test_set)).execute()
array([[ False,  True],
       [ True,  False]])
```
