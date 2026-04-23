# maxframe.tensor.where

### maxframe.tensor.where(condition, x=None, y=None)

Return elements, either from x or y, depending on condition.

If only condition is given, return `condition.nonzero()`.

* **Parameters:**
  * **condition** (*array_like* *,* [*bool*](https://docs.python.org/3/library/functions.html#bool)) – When True, yield x, otherwise yield y.
  * **x** (*array_like* *,* *optional*) – Values from which to choose. x, y and condition need to be
    broadcastable to some shape.
  * **y** (*array_like* *,* *optional*) – Values from which to choose. x, y and condition need to be
    broadcastable to some shape.
* **Returns:**
  **out** – If both x and y are specified, the output tensor contains
  elements of x where condition is True, and elements from
  y elsewhere.

  If only condition is given, return the tuple
  `condition.nonzero()`, the indices where condition is True.
* **Return type:**
  Tensor or [tuple](https://docs.python.org/3/library/stdtypes.html#tuple) of Tensors

#### SEE ALSO
[`nonzero`](maxframe.tensor.nonzero.md#maxframe.tensor.nonzero), [`choose`](maxframe.tensor.choose.md#maxframe.tensor.choose)

### Notes

If x and y are given and input arrays are 1-D, where is
equivalent to:

```default
[xv if c else yv for (c,xv,yv) in zip(condition,x,y)]
```

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.where([[True, False], [True, True]],
...          [[1, 2], [3, 4]],
...          [[9, 8], [7, 6]]).execute()
array([[1, 8],
       [3, 4]])
```

```pycon
>>> mt.where([[0, 1], [1, 0]]).execute()
(array([0, 1]), array([1, 0]))
```

```pycon
>>> x = mt.arange(9.).reshape(3, 3)
>>> mt.where( x > 5 ).execute()
(array([2, 2, 2]), array([0, 1, 2]))
>>> mt.where(x < 5, x, -1).execute()               # Note: broadcasting.
array([[ 0.,  1.,  2.],
       [ 3.,  4., -1.],
       [-1., -1., -1.]])
```

Find the indices of elements of x that are in goodvalues.

```pycon
>>> goodvalues = [3, 4, 7]
>>> ix = mt.isin(x, goodvalues)
>>> ix.execute()
array([[False, False, False],
       [ True,  True, False],
       [False,  True, False]])
>>> mt.where(ix).execute()
(array([1, 1, 2]), array([0, 1, 1]))
```
