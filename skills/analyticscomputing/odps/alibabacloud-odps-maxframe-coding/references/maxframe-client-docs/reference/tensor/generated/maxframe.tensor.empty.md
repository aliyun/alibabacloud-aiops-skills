# maxframe.tensor.empty

### maxframe.tensor.empty(shape, dtype=None, chunk_size=None, gpu=None, order='C')

Return a new tensor of given shape and type, without initializing entries.

* **Parameters:**
  * **shape** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int)) – Shape of the empty tensor
  * **dtype** (*data-type* *,* *optional*) – Desired output data-type.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional* *,* *default: 'C'*) – Whether to store multi-dimensional data in row-major
    (C-style) or column-major (Fortran-style) order in
    memory.
* **Returns:**
  **out** – Tensor of uninitialized (arbitrary) data of the given shape, dtype, and
  order.  Object arrays will be initialized to None.
* **Return type:**
  Tensor

#### SEE ALSO
[`empty_like`](maxframe.tensor.empty_like.md#maxframe.tensor.empty_like), [`zeros`](maxframe.tensor.zeros.md#maxframe.tensor.zeros), [`ones`](maxframe.tensor.ones.md#maxframe.tensor.ones)

### Notes

empty, unlike zeros, does not set the array values to zero,
and may therefore be marginally faster.  On the other hand, it requires
the user to manually set all the values in the array, and should be
used with caution.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.empty([2, 2]).execute()
array([[ -9.74499359e+001,   6.69583040e-309],
       [  2.13182611e-314,   3.06959433e-309]])         #random
>>> mt.empty([2, 2], dtype=int).execute()
array([[-1073741821, -1067949133],
       [  496041986,    19249760]])                     #random
```
