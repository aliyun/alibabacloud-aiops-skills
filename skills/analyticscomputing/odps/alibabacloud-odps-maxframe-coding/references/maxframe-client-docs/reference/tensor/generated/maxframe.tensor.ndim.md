# maxframe.tensor.ndim

### maxframe.tensor.ndim(a)

Return the number of dimensions of a tensor.

* **Parameters:**
  **a** (*array_like*) – Input tebsir.  If it is not already a tensor, a conversion is
  attempted.
* **Returns:**
  **number_of_dimensions** – The number of dimensions in a.  Scalars are zero-dimensional.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
`ndarray.ndim`
: equivalent method

[`shape`](maxframe.tensor.shape.md#maxframe.tensor.shape)
: dimensions of tensor

`Tensor.shape`
: dimensions of tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.ndim([[1,2,3],[4,5,6]])
2
>>> mt.ndim(mt.array([[1,2,3],[4,5,6]]))
2
>>> mt.ndim(1)
0
```
