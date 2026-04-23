# maxframe.tensor.repeat

### maxframe.tensor.repeat(a, repeats, axis=None)

Repeat elements of a tensor.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **repeats** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *tensor* *of* *ints*) – The number of repetitions for each element.  repeats is broadcasted
    to fit the shape of the given axis.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which to repeat values.  By default, use the
    flattened input tensor, and return a flat output tensor.
* **Returns:**
  **repeated_tensor** – Output array which has the same shape as a, except along
  the given axis.
* **Return type:**
  Tensor

#### SEE ALSO
[`tile`](maxframe.tensor.tile.md#maxframe.tensor.tile)
: Tile a tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.repeat(3, 4).execute()
array([3, 3, 3, 3])
>>> x = mt.array([[1,2],[3,4]])
>>> mt.repeat(x, 2).execute()
array([1, 1, 2, 2, 3, 3, 4, 4])
>>> mt.repeat(x, 3, axis=1).execute()
array([[1, 1, 1, 2, 2, 2],
       [3, 3, 3, 4, 4, 4]])
>>> mt.repeat(x, [1, 2], axis=0).execute()
array([[1, 2],
       [3, 4],
       [3, 4]])
```
