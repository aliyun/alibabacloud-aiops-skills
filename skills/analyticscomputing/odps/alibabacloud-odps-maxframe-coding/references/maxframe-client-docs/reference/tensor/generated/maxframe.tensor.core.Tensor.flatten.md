# maxframe.tensor.core.Tensor.flatten

#### Tensor.flatten(order='C')

Return a copy of the tensor collapsed into one dimension.

* **Parameters:**
  **order** ( *{'C'* *,*  *'F'* *,*  *'A'* *,*  *'K'}* *,* *optional*) – ‘C’ means to flatten in row-major (C-style) order.
  ‘F’ means to flatten in column-major (Fortran-
  style) order. ‘A’ means to flatten in column-major
  order if a is Fortran *contiguous* in memory,
  row-major order otherwise. ‘K’ means to flatten
  a in the order the elements occur in memory.
  The default is ‘C’.
* **Returns:**
  **y** – A copy of the input tensor, flattened to one dimension.
* **Return type:**
  Tensor

#### SEE ALSO
`ravel`
: Return a flattened tensor.

`flat`
: A 1-D flat iterator over the tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1,2], [3,4]])
>>> a.flatten().execute()
array([1, 2, 3, 4])
```
