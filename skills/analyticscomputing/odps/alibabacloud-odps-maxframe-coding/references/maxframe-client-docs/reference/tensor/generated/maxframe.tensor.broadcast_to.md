# maxframe.tensor.broadcast_to

### maxframe.tensor.broadcast_to(tensor, shape)

Broadcast a tensor to a new shape.

* **Parameters:**
  * **tensor** (*array_like*) – The tensor to broadcast.
  * **shape** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – The shape of the desired array.
* **Returns:**
  **broadcast**
* **Return type:**
  Tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If the tensor is not compatible with the new shape according to MaxFrame’s
      broadcasting rules.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([1, 2, 3])
>>> mt.broadcast_to(x, (3, 3)).execute()
array([[1, 2, 3],
       [1, 2, 3],
       [1, 2, 3]])
```
