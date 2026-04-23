# maxframe.tensor.roll

### maxframe.tensor.roll(a, shift, axis=None)

Roll tensor elements along a given axis.

Elements that roll beyond the last position are re-introduced at
the first.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **shift** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints*) – The number of places by which elements are shifted.  If a tuple,
    then axis must be a tuple of the same size, and each of the
    given axes is shifted by the corresponding number.  If an int
    while axis is a tuple of ints, then the same value is used for
    all given axes.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Axis or axes along which elements are shifted.  By default, the
    tensor is flattened before shifting, after which the original
    shape is restored.
* **Returns:**
  **res** – Output tensor, with the same shape as a.
* **Return type:**
  Tensor

#### SEE ALSO
[`rollaxis`](maxframe.tensor.rollaxis.md#maxframe.tensor.rollaxis)
: Roll the specified axis backwards, until it lies in a given position.

### Notes

Supports rolling over multiple dimensions simultaneously.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(10)
>>> mt.roll(x, 2).execute()
array([8, 9, 0, 1, 2, 3, 4, 5, 6, 7])
```

```pycon
>>> x2 = mt.reshape(x, (2,5))
>>> x2.execute()
array([[0, 1, 2, 3, 4],
       [5, 6, 7, 8, 9]])
>>> mt.roll(x2, 1).execute()
array([[9, 0, 1, 2, 3],
       [4, 5, 6, 7, 8]])
>>> mt.roll(x2, 1, axis=0).execute()
array([[5, 6, 7, 8, 9],
       [0, 1, 2, 3, 4]])
>>> mt.roll(x2, 1, axis=1).execute()
array([[4, 0, 1, 2, 3],
       [9, 5, 6, 7, 8]])
```
