# maxframe.tensor.fill_diagonal

### maxframe.tensor.fill_diagonal(a, val, wrap=False)

Fill the main diagonal of the given tensor of any dimensionality.

For a tensor a with `a.ndim >= 2`, the diagonal is the list of
locations with indices `a[i, ..., i]` all identical. This function
modifies the input tensor in-place, it does not return a value.

* **Parameters:**
  * **a** (*Tensor* *,* *at least 2-D.*) – Tensor whose diagonal is to be filled, it gets modified in-place.
  * **val** (*scalar*) – Value to be written on the diagonal, its type must be compatible with
    that of the tensor a.
  * **wrap** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – For tall matrices in NumPy version up to 1.6.2, the
    diagonal “wrapped” after N columns. You can have this behavior
    with this option. This affects only tall matrices.

#### SEE ALSO
`diag_indices`, `diag_indices_from`

### Notes

This functionality can be obtained via diag_indices, but internally
this version uses a much faster implementation that never constructs the
indices and uses simple slicing.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.zeros((3, 3), int)
>>> mt.fill_diagonal(a, 5)
>>> a.execute()
array([[5, 0, 0],
       [0, 5, 0],
       [0, 0, 5]])
```

The same function can operate on a 4-D tensor:

```pycon
>>> a = mt.zeros((3, 3, 3, 3), int)
>>> mt.fill_diagonal(a, 4)
```

We only show a few blocks for clarity:

```pycon
>>> a[0, 0].execute()
array([[4, 0, 0],
       [0, 0, 0],
       [0, 0, 0]])
>>> a[1, 1].execute()
array([[0, 0, 0],
       [0, 4, 0],
       [0, 0, 0]])
>>> a[2, 2].execute()
array([[0, 0, 0],
       [0, 0, 0],
       [0, 0, 4]])
```

The wrap option affects only tall matrices:

```pycon
>>> # tall matrices no wrap
>>> a = mt.zeros((5, 3), int)
>>> mt.fill_diagonal(a, 4)
>>> a.execute()
array([[4, 0, 0],
       [0, 4, 0],
       [0, 0, 4],
       [0, 0, 0],
       [0, 0, 0]])
```

```pycon
>>> # tall matrices wrap
>>> a = mt.zeros((5, 3), int)
>>> mt.fill_diagonal(a, 4, wrap=True)
>>> a.execute()
array([[4, 0, 0],
       [0, 4, 0],
       [0, 0, 4],
       [0, 0, 0],
       [4, 0, 0]])
```

```pycon
>>> # wide matrices
>>> a = mt.zeros((3, 5), int)
>>> mt.fill_diagonal(a, 4, wrap=True)
>>> a.execute()
array([[4, 0, 0, 0, 0],
       [0, 4, 0, 0, 0],
       [0, 0, 4, 0, 0]])
```

The anti-diagonal can be filled by reversing the order of elements
using either numpy.flipud or numpy.fliplr.

```pycon
>>> a = mt.zeros((3, 3), int)
>>> mt.fill_diagonal(mt.fliplr(a), [1,2,3])  # Horizontal flip
>>> a.execute()
array([[0, 0, 1],
       [0, 2, 0],
       [3, 0, 0]])
>>> mt.fill_diagonal(mt.flipud(a), [1,2,3])  # Vertical flip
>>> a.execute()
array([[0, 0, 3],
       [0, 2, 0],
       [1, 0, 0]])
```

Note that the order in which the diagonal is filled varies depending
on the flip function.
