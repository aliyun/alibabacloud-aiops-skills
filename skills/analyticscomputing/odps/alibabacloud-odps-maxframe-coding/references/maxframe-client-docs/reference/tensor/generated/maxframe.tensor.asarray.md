# maxframe.tensor.asarray

### maxframe.tensor.asarray(x, dtype=None, order=None, chunk_size=None)

Convert the input to an array.

* **Parameters:**
  * **a** (*array_like*) – Input data, in any form that can be converted to a tensor.  This
    includes lists, lists of tuples, tuples, tuples of tuples, tuples
    of lists and tensors.
  * **dtype** (*data-type* *,* *optional*) – By default, the data-type is inferred from the input data.
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional*) – Whether to use row-major (C-style) or
    column-major (Fortran-style) memory representation.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *optional*) – Specifies chunk size for each dimension.
* **Returns:**
  **out** – Tensor interpretation of a.  No copy is performed if the input
  is already an ndarray with matching dtype and order.  If a is a
  subclass of ndarray, a base class ndarray is returned.
* **Return type:**
  Tensor

#### SEE ALSO
`ascontiguousarray`
: Convert input to a contiguous tensor.

`asfortranarray`
: Convert input to a tensor with column-major memory order.

### Examples

Convert a list into a tensor:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = [1, 2]
>>> mt.asarray(a).execute()
array([1, 2])
```

Existing arrays are not copied:

```pycon
>>> a = mt.array([1, 2])
>>> mt.asarray(a) is a
True
```

If dtype is set, array is copied only if dtype does not match:

```pycon
>>> a = mt.array([1, 2], dtype=mt.float32)
>>> mt.asarray(a, dtype=mt.float32) is a
True
>>> mt.asarray(a, dtype=mt.float64) is a
False
```
