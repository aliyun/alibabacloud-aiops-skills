# maxframe.tensor.power

### maxframe.tensor.power(x1, x2, out=None, where=None, \*\*kwargs)

First tensor elements raised to powers from second tensor, element-wise.

Raise each base in x1 to the positionally-corresponding power in
x2.  x1 and x2 must be broadcastable to the same shape. Note that an
integer type raised to a negative integer power will raise a ValueError.

* **Parameters:**
  * **x1** (*array_like*) – The bases.
  * **x2** (*array_like*) – The exponents.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The bases in x1 raised to the exponents in x2.
* **Return type:**
  Tensor

#### SEE ALSO
[`float_power`](maxframe.tensor.float_power.md#maxframe.tensor.float_power)
: power function that promotes integers to float

### Examples

Cube each element in a list.

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x1 = range(6)
>>> x1
[0, 1, 2, 3, 4, 5]
>>> mt.power(x1, 3).execute()
array([  0,   1,   8,  27,  64, 125])
```

Raise the bases to different exponents.

```pycon
>>> x2 = [1.0, 2.0, 3.0, 3.0, 2.0, 1.0]
>>> mt.power(x1, x2).execute()
array([  0.,   1.,   8.,  27.,  16.,   5.])
```

The effect of broadcasting.

```pycon
>>> x2 = mt.array([[1, 2, 3, 3, 2, 1], [1, 2, 3, 3, 2, 1]])
>>> x2.execute()
array([[1, 2, 3, 3, 2, 1],
       [1, 2, 3, 3, 2, 1]])
>>> mt.power(x1, x2).execute()
array([[ 0,  1,  8, 27, 16,  5],
       [ 0,  1,  8, 27, 16,  5]])
```
