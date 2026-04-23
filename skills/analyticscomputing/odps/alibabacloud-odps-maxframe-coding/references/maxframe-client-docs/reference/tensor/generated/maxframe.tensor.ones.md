# maxframe.tensor.ones

### maxframe.tensor.ones(shape, dtype=None, chunk_size=None, gpu=None, order='C')

Return a new tensor of given shape and type, filled with ones.

* **Parameters:**
  * **shape** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *ints*) – Shape of the new tensor, e.g., `(2, 3)` or `2`.
  * **dtype** (*data-type* *,* *optional*) – The desired data-type for the tensor, e.g., mt.int8.  Default is
    mt.float64.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional* *,* *default: C*) – Whether to store multi-dimensional data in row-major
    (C-style) or column-major (Fortran-style) order in
    memory.
* **Returns:**
  **out** – Tensor of ones with the given shape, dtype, and order.
* **Return type:**
  Tensor

#### SEE ALSO
[`zeros`](maxframe.tensor.zeros.md#maxframe.tensor.zeros), `ones_like`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.ones(5).execute()
array([ 1.,  1.,  1.,  1.,  1.])
```

```pycon
>>> mt.ones((5,), dtype=int).execute()
array([1, 1, 1, 1, 1])
```

```pycon
>>> mt.ones((2, 1)).execute()
array([[ 1.],
       [ 1.]])
```

```pycon
>>> s = (2,2)
>>> mt.ones(s).execute()
array([[ 1.,  1.],
       [ 1.,  1.]])
```
