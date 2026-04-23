# maxframe.tensor.concatenate

### maxframe.tensor.concatenate(tensors, axis=0)

Join a sequence of arrays along an existing axis.

* **Parameters:**
  * **a1** (*sequence* *of* *array_like*) – The tensors must have the same shape, except in the dimension
    corresponding to axis (the first, by default).
  * **a2** (*sequence* *of* *array_like*) – The tensors must have the same shape, except in the dimension
    corresponding to axis (the first, by default).
  * **...** (*sequence* *of* *array_like*) – The tensors must have the same shape, except in the dimension
    corresponding to axis (the first, by default).
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which the tensors will be joined.  Default is 0.
* **Returns:**
  **res** – The concatenated tensor.
* **Return type:**
  Tensor

#### SEE ALSO
`stack`
: Stack a sequence of tensors along a new axis.

[`vstack`](maxframe.tensor.vstack.md#maxframe.tensor.vstack)
: Stack tensors in sequence vertically (row wise)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([[1, 2], [3, 4]])
>>> b = mt.array([[5, 6]])
>>> mt.concatenate((a, b), axis=0).execute()
array([[1, 2],
       [3, 4],
       [5, 6]])
>>> mt.concatenate((a, b.T), axis=1).execute()
array([[1, 2, 5],
       [3, 4, 6]])
```
