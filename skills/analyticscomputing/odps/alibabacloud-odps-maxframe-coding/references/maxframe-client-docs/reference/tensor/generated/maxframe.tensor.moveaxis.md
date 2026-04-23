# maxframe.tensor.moveaxis

### maxframe.tensor.moveaxis(a, source, destination)

Move axes of a tensor to new positions.

Other axes remain in their original order.

* **Parameters:**
  * **a** (*Tensor*) – The tensor whose axes should be reordered.
  * **source** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* [*int*](https://docs.python.org/3/library/functions.html#int)) – Original positions of the axes to move. These must be unique.
  * **destination** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* [*int*](https://docs.python.org/3/library/functions.html#int)) – Destination positions for each of the original axes. These must also be
    unique.
* **Returns:**
  **result** – Array with moved axes. This tensor is a view of the input tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`transpose`](maxframe.tensor.transpose.md#maxframe.tensor.transpose)
: Permute the dimensions of an array.

[`swapaxes`](maxframe.tensor.swapaxes.md#maxframe.tensor.swapaxes)
: Interchange two axes of an array.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.zeros((3, 4, 5))
>>> mt.moveaxis(x, 0, -1).shape
(4, 5, 3)
>>> mt.moveaxis(x, -1, 0).shape
(5, 3, 4),
```

These all achieve the same result:

```pycon
>>> mt.transpose(x).shape
(5, 4, 3)
>>> mt.swapaxes(x, 0, -1).shape
(5, 4, 3)
>>> mt.moveaxis(x, [0, 1], [-1, -2]).shape
(5, 4, 3)
>>> mt.moveaxis(x, [0, 1, 2], [-1, -2, -3]).shape
(5, 4, 3)
```
