# maxframe.tensor.array

### maxframe.tensor.array(x, dtype=None, copy=True, order='K', ndmin=None, chunk_size=None)

Create a tensor.

* **Parameters:**
  * **object** (*array_like*) – An array, any object exposing the array interface, an object whose
    \_\_array_\_ method returns an array, or any (nested) sequence.
  * **dtype** (*data-type* *,* *optional*) – The desired data-type for the array.  If not given, then the type will
    be determined as the minimum type required to hold the objects in the
    sequence.  This argument can only be used to ‘upcast’ the array.  For
    downcasting, use the .astype(t) method.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If true (default), then the object is copied.  Otherwise, a copy will
    only be made if \_\_array_\_ returns a copy, if obj is a nested sequence,
    or if a copy is needed to satisfy any of the other requirements
    (dtype, order, etc.).
  * **order** ( *{'K'* *,*  *'A'* *,*  *'C'* *,*  *'F'}* *,* *optional*) – 

    Specify the memory layout of the array. If object is not an array, the
    newly created array will be in C order (row major) unless ‘F’ is
    specified, in which case it will be in Fortran order (column major).
    If object is an array the following holds.

    | order   | no copy   | copy=True                                           |
    |---------|-----------|-----------------------------------------------------|
    | ’K’     | unchanged | F & C order preserved, otherwise most similar order |
    | ’A’     | unchanged | F order if input is F and not C, otherwise C order  |
    | ’C’     | C order   | C order                                             |
    | ’F’     | F order   | F order                                             |

    When `copy=False` and a copy is made for other reasons, the result is
    the same as if `copy=True`, with some exceptions for A, see the
    Notes section. The default order is ‘K’.
  * **ndmin** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Specifies the minimum number of dimensions that the resulting
    array should have.  Ones will be prepended to the shape as
    needed to meet this requirement.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *optional*) – Specifies chunk size for each dimension.
* **Returns:**
  **out** – An tensor object satisfying the specified requirements.
* **Return type:**
  Tensor

#### SEE ALSO
[`empty`](maxframe.tensor.empty.md#maxframe.tensor.empty), [`empty_like`](maxframe.tensor.empty_like.md#maxframe.tensor.empty_like), [`zeros`](maxframe.tensor.zeros.md#maxframe.tensor.zeros), `zeros_like`, [`ones`](maxframe.tensor.ones.md#maxframe.tensor.ones), `ones_like`, [`full`](maxframe.tensor.full.md#maxframe.tensor.full), [`full_like`](maxframe.tensor.full_like.md#maxframe.tensor.full_like)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.array([1, 2, 3]).execute()
array([1, 2, 3])
```

Upcasting:

```pycon
>>> mt.array([1, 2, 3.0]).execute()
array([ 1.,  2.,  3.])
```

More than one dimension:

```pycon
>>> mt.array([[1, 2], [3, 4]]).execute()
array([[1, 2],
       [3, 4]])
```

Minimum dimensions 2:

```pycon
>>> mt.array([1, 2, 3], ndmin=2).execute()
array([[1, 2, 3]])
```

Type provided:

```pycon
>>> mt.array([1, 2, 3], dtype=complex).execute()
array([ 1.+0.j,  2.+0.j,  3.+0.j])
```
