# maxframe.tensor.indices

### maxframe.tensor.indices(dimensions, dtype=<class 'int'>, chunk_size=None)

Return a tensor representing the indices of a grid.

Compute a tensor where the subtensors contain index values 0,1,…
varying only along the corresponding axis.

* **Parameters:**
  * **dimensions** (*sequence* *of* *ints*) – The shape of the grid.
  * **dtype** (*dtype* *,* *optional*) – Data type of the result.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **grid** – The tensor of grid indices,
  `grid.shape = (len(dimensions),) + tuple(dimensions)`.
* **Return type:**
  Tensor

#### SEE ALSO
[`mgrid`](maxframe.tensor.mgrid.md#maxframe.tensor.mgrid), [`meshgrid`](maxframe.tensor.meshgrid.md#maxframe.tensor.meshgrid)

### Notes

The output shape is obtained by prepending the number of dimensions
in front of the tuple of dimensions, i.e. if dimensions is a tuple
`(r0, ..., rN-1)` of length `N`, the output shape is
`(N,r0,...,rN-1)`.

The subtensors `grid[k]` contains the N-D array of indices along the
`k-th` axis. Explicitly:

```default
grid[k,i0,i1,...,iN-1] = ik
```

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> grid = mt.indices((2, 3))
>>> grid.shape
(2, 2, 3)
>>> grid[0].execute()        # row indices
array([[0, 0, 0],
       [1, 1, 1]])
>>> grid[1].execute()        # column indices
array([[0, 1, 2],
       [0, 1, 2]])
```

The indices can be used as an index into a tensor.

```pycon
>>> x = mt.arange(20).reshape(5, 4)
>>> row, col = mt.indices((2, 3))
>>> # x[row, col]
```

Note that it would be more straightforward in the above example to
extract the required elements directly with `x[:2, :3]`.
