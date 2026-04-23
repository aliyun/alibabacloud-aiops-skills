# maxframe.tensor.reshape

### maxframe.tensor.reshape(a, newshape, order='C')

Gives a new shape to a tensor without changing its data.

* **Parameters:**
  * **a** (*array_like*) – Tensor to be reshaped.
  * **newshape** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints*) – The new shape should be compatible with the original shape. If
    an integer, then the result will be a 1-D tensor of that length.
    One shape dimension can be -1. In this case, the value is
    inferred from the length of the tensor and remaining dimensions.
  * **order** ( *{'C'* *,*  *'F'* *,*  *'A'}* *,* *optional*) – Read the elements of a using this index order, and place the
    elements into the reshaped array using this index order.  ‘C’
    means to read / write the elements using C-like index order,
    with the last axis index changing fastest, back to the first
    axis index changing slowest. ‘F’ means to read / write the
    elements using Fortran-like index order, with the first index
    changing fastest, and the last index changing slowest. Note that
    the ‘C’ and ‘F’ options take no account of the memory layout of
    the underlying array, and only refer to the order of indexing.
    ‘A’ means to read / write the elements in Fortran-like index
    order if a is Fortran *contiguous* in memory, C-like order
    otherwise.
* **Returns:**
  **reshaped_array** – This will be a new view object if possible; otherwise, it will
  be a copy.
* **Return type:**
  Tensor

#### SEE ALSO
`Tensor.reshape`
: Equivalent method.

### Notes

It is not always possible to change the shape of a tensor without
copying the data. If you want an error to be raised when the data is copied,
you should assign the new shape to the shape attribute of the array:

```default
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.arange(6).reshape((3, 2))
>>> a.execute()
array([[0, 1],
       [2, 3],
       [4, 5]])
```

You can think of reshaping as first raveling the tensor (using the given
index order), then inserting the elements from the raveled tensor into the
new tensor using the same kind of index ordering as was used for the
raveling.

```pycon
>>> mt.reshape(a, (2, 3)).execute()
array([[0, 1, 2],
       [3, 4, 5]])
>>> mt.reshape(mt.ravel(a), (2, 3)).execute()
array([[0, 1, 2],
       [3, 4, 5]])
```

### Examples

```pycon
>>> a = mt.array([[1,2,3], [4,5,6]])
>>> mt.reshape(a, 6).execute()
array([1, 2, 3, 4, 5, 6])
```

```pycon
>>> mt.reshape(a, (3,-1)).execute()       # the unspecified value is inferred to be 2
array([[1, 2],
       [3, 4],
       [5, 6]])
```
