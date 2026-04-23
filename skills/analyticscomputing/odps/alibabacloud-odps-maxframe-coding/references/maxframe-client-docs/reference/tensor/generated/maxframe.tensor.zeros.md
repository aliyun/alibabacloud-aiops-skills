# maxframe.tensor.zeros

### maxframe.tensor.zeros(shape, dtype=None, chunk_size=None, gpu=None, sparse=False, order='C')

Return a new tensor of given shape and type, filled with zeros.

* **Parameters:**
  * **shape** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *ints*) – Shape of the new tensor, e.g., `(2, 3)` or `2`.
  * **dtype** (*data-type* *,* *optional*) – The desired data-type for the array, e.g., mt.int8.  Default is
    mt.float64.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Create sparse tensor if True, False as default
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional* *,* *default: 'C'*) – Whether to store multi-dimensional data in row-major
    (C-style) or column-major (Fortran-style) order in
    memory.
* **Returns:**
  **out** – Tensor of zeros with the given shape, dtype, and order.
* **Return type:**
  Tensor

#### SEE ALSO
`zeros_like`
: Return a tensor of zeros with shape and type of input.

`ones_like`
: Return a tensor of ones with shape and type of input.

[`empty_like`](maxframe.tensor.empty_like.md#maxframe.tensor.empty_like)
: Return a empty tensor with shape and type of input.

[`ones`](maxframe.tensor.ones.md#maxframe.tensor.ones)
: Return a new tensor setting values to one.

[`empty`](maxframe.tensor.empty.md#maxframe.tensor.empty)
: Return a new uninitialized tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.zeros(5).execute()
array([ 0.,  0.,  0.,  0.,  0.])
```

```pycon
>>> mt.zeros((5,), dtype=int).execute()
array([0, 0, 0, 0, 0])
```

```pycon
>>> mt.zeros((2, 1)).execute()
array([[ 0.],
       [ 0.]])
```

```pycon
>>> s = (2,2)
>>> mt.zeros(s).execute()
array([[ 0.,  0.],
       [ 0.,  0.]])
```

```pycon
>>> mt.zeros((2,), dtype=[('x', 'i4'), ('y', 'i4')]).execute() # custom dtype
array([(0, 0), (0, 0)],
      dtype=[('x', '<i4'), ('y', '<i4')])
```
