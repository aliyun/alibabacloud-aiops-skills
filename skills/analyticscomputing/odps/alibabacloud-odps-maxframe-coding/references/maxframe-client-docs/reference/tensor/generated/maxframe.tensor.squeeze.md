# maxframe.tensor.squeeze

### maxframe.tensor.squeeze(a, axis=None)

Remove single-dimensional entries from the shape of a tensor.

* **Parameters:**
  * **a** (*array_like*) – Input data.
  * **axis** (*None* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Selects a subset of the single-dimensional entries in the
    shape. If an axis is selected with shape entry greater than
    one, an error is raised.
* **Returns:**
  **squeezed** – The input tensor, but with all or a subset of the
  dimensions of length 1 removed. This is always a itself
  or a view into a.
* **Return type:**
  Tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If axis is not None, and an axis being squeezed is not of length 1

#### SEE ALSO
[`expand_dims`](maxframe.tensor.expand_dims.md#maxframe.tensor.expand_dims)
: The inverse operation, adding singleton dimensions

[`reshape`](maxframe.tensor.reshape.md#maxframe.tensor.reshape)
: Insert, remove, and combine dimensions, and resize existing ones

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[[0], [1], [2]]])
>>> x.shape
(1, 3, 1)
>>> mt.squeeze(x).shape
(3,)
>>> mt.squeeze(x, axis=0).shape
(3, 1)
>>> mt.squeeze(x, axis=1).shape
Traceback (most recent call last):
...
ValueError: cannot select an axis to squeeze out which has size not equal to one
>>> mt.squeeze(x, axis=2).shape
(1, 3)
```
