# maxframe.tensor.left_shift

### maxframe.tensor.left_shift(x1, x2, out=None, where=None, \*\*kwargs)

Shift the bits of an integer to the left.

Bits are shifted to the left by appending x2 0s at the right of x1.
Since the internal representation of numbers is in binary format, this
operation is equivalent to multiplying x1 by `2**x2`.

* **Parameters:**
  * **x1** (*array_like* *of* *integer type*) – Input values.
  * **x2** (*array_like* *of* *integer type*) – Number of zeros to append to x1. Has to be non-negative.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Return x1 with bits shifted x2 times to the left.
* **Return type:**
  tensor of integer type

#### SEE ALSO
[`right_shift`](maxframe.tensor.right_shift.md#maxframe.tensor.right_shift)
: Shift the bits of an integer to the right.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.left_shift(5, 2).execute()
20
```

```pycon
>>> mt.left_shift(5, [1,2,3]).execute()
array([10, 20, 40])
```
