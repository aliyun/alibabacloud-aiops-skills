# maxframe.tensor.ravel

### maxframe.tensor.ravel(a, order='C')

Return a contiguous flattened tensor.

A 1-D tensor, containing the elements of the input, is returned.  A copy is
made only if needed.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.  The elements in a are packed as a 1-D tensor.
  * **order** ( *{'C'* *,* *'F'* *,*  *'A'* *,*  *'K'}* *,* *optional*) – The elements of a are read using this index order. ‘C’ means
    to index the elements in row-major, C-style order,
    with the last axis index changing fastest, back to the first
    axis index changing slowest.  ‘F’ means to index the elements
    in column-major, Fortran-style order, with the
    first index changing fastest, and the last index changing
    slowest. Note that the ‘C’ and ‘F’ options take no account of
    the memory layout of the underlying array, and only refer to
    the order of axis indexing.  ‘A’ means to read the elements in
    Fortran-like index order if a is Fortran *contiguous* in
    memory, C-like order otherwise.  ‘K’ means to read the
    elements in the order they occur in memory, except for
    reversing the data when strides are negative.  By default, ‘C’
    index order is used.
* **Returns:**
  **y** – If a is a matrix, y is a 1-D tensor, otherwise y is a tensor of
  the same subtype as a. The shape of the returned array is
  `(a.size,)`. Matrices are special cased for backward
  compatibility.
* **Return type:**
  array_like

#### SEE ALSO
`Tensor.flat`
: 1-D iterator over an array.

`Tensor.flatten`
: 1-D array copy of the elements of an array in row-major order.

`Tensor.reshape`
: Change the shape of an array without changing its data.

### Examples

It is equivalent to `reshape(-1)`.

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[1, 2, 3], [4, 5, 6]])
>>> print(mt.ravel(x).execute())
[1 2 3 4 5 6]
```

```pycon
>>> print(x.reshape(-1).execute())
[1 2 3 4 5 6]
```

```pycon
>>> print(mt.ravel(x.T).execute())
[1 4 2 5 3 6]
```

```pycon
>>> a = mt.arange(12).reshape(2,3,2).swapaxes(1,2); a.execute()
array([[[ 0,  2,  4],
        [ 1,  3,  5]],
       [[ 6,  8, 10],
        [ 7,  9, 11]]])
>>> a.ravel().execute()
array([ 0,  2,  4,  1,  3,  5,  6,  8, 10,  7,  9, 11])
```
