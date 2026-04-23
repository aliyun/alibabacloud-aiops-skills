# maxframe.tensor.unravel_index

### maxframe.tensor.unravel_index(indices, dims, order='C')

Converts a flat index or tensor of flat indices into a tuple
of coordinate tensors.

* **Parameters:**
  * **indices** (*array_like*) – An integer tensor whose elements are indices into the flattened
    version of a tensor of dimensions `dims`.
  * **dims** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints*) – The shape of the tensor to use for unraveling `indices`.
  * **order** ( *{'C'* *,*  *'F'}* *,* *optional*) – Determines whether the indices should be viewed as indexing in
    row-major (C-style) or column-major (Fortran-style) order.
* **Returns:**
  **unraveled_coords** – Each tensor in the tuple has the same shape as the `indices`
  tensor.
* **Return type:**
  [tuple](https://docs.python.org/3/library/stdtypes.html#tuple) of Tensor

#### SEE ALSO
`ravel_multi_index`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.unravel_index([22, 41, 37], (7,6)).execute()
(array([3, 6, 6]), array([4, 5, 1]))
```

```pycon
>>> mt.unravel_index(1621, (6,7,8,9)).execute()
(3, 1, 4, 1)
```
