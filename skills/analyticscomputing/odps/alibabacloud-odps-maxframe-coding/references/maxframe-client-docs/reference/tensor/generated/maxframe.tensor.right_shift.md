# maxframe.tensor.right_shift

### maxframe.tensor.right_shift(x1, x2, out=None, where=None, \*\*kwargs)

Shift the bits of an integer to the right.

Bits are shifted to the right x2.  Because the internal
representation of numbers is in binary format, this operation is
equivalent to dividing x1 by `2**x2`.

* **Parameters:**
  * **x1** (*array_like* *,* [*int*](https://docs.python.org/3/library/functions.html#int)) – Input values.
  * **x2** (*array_like* *,* [*int*](https://docs.python.org/3/library/functions.html#int)) – Number of bits to remove at the right of x1.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Return x1 with bits shifted x2 times to the right.
* **Return type:**
  Tensor, [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`left_shift`](maxframe.tensor.left_shift.md#maxframe.tensor.left_shift)
: Shift the bits of an integer to the left.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.right_shift(10, 1).execute()
5
```

```pycon
>>> mt.right_shift(10, [1,2,3]).execute()
array([5, 2, 1])
```
