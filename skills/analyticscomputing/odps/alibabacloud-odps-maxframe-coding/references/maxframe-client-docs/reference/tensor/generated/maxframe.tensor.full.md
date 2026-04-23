# maxframe.tensor.full

### maxframe.tensor.full(shape, fill_value, dtype=None, chunk_size=None, gpu=None, order='C')

Return a new tensor of given shape and type, filled with fill_value.

* **Parameters:**
  * **shape** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *ints*) – Shape of the new tensor, e.g., `(2, 3)` or `2`.
  * **fill_value** (*scalar*) – Fill value.
  * **dtype** (*data-type* *,* *optional*) – 

    The desired data-type for the tensor  The default, None, means
    : np.array(fill_value).dtype.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional*) – Whether to store multidimensional data in C- or Fortran-contiguous
    (row- or column-wise) order in memory.
* **Returns:**
  **out** – Tensor of fill_value with the given shape, dtype, and order.
* **Return type:**
  Tensor

#### SEE ALSO
`zeros_like`
: Return a tensor of zeros with shape and type of input.

`ones_like`
: Return a tensor of ones with shape and type of input.

[`empty_like`](maxframe.tensor.empty_like.md#maxframe.tensor.empty_like)
: Return an empty tensor with shape and type of input.

[`full_like`](maxframe.tensor.full_like.md#maxframe.tensor.full_like)
: Fill a tensor with shape and type of input.

[`zeros`](maxframe.tensor.zeros.md#maxframe.tensor.zeros)
: Return a new tensor setting values to zero.

[`ones`](maxframe.tensor.ones.md#maxframe.tensor.ones)
: Return a new tensor setting values to one.

[`empty`](maxframe.tensor.empty.md#maxframe.tensor.empty)
: Return a new uninitialized tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.full((2, 2), mt.inf).execute()
array([[ inf,  inf],
       [ inf,  inf]])
>>> mt.full((2, 2), 10).execute()
array([[10, 10],
       [10, 10]])
```
