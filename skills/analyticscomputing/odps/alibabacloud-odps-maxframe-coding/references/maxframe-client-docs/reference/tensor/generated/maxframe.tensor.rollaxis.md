# maxframe.tensor.rollaxis

### maxframe.tensor.rollaxis(tensor, axis, start=0)

Roll the specified axis backwards, until it lies in a given position.

This function continues to be supported for backward compatibility, but you
should prefer moveaxis.

* **Parameters:**
  * **a** (*Tensor*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The axis to roll backwards.  The positions of the other axes do not
    change relative to one another.
  * **start** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis is rolled until it lies before this position.  The default,
    0, results in a “complete” roll.
* **Returns:**
  **res** – a view of a is always returned.
* **Return type:**
  Tensor

#### SEE ALSO
[`moveaxis`](maxframe.tensor.moveaxis.md#maxframe.tensor.moveaxis)
: Move array axes to new positions.

[`roll`](maxframe.tensor.roll.md#maxframe.tensor.roll)
: Roll the elements of an array by a number of positions along a given axis.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.ones((3,4,5,6))
>>> mt.rollaxis(a, 3, 1).shape
(3, 6, 4, 5)
>>> mt.rollaxis(a, 2).shape
(5, 3, 4, 6)
>>> mt.rollaxis(a, 1, 4).shape
(3, 5, 6, 4)
```
