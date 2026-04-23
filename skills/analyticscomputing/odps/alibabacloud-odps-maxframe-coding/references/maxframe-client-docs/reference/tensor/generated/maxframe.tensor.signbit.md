# maxframe.tensor.signbit

### maxframe.tensor.signbit(x, out=None, where=None, \*\*kwargs)

Returns element-wise True where signbit is set (less than zero).

* **Parameters:**
  * **x** (*array_like*) – The input value(s).
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **result** – Output tensor, or reference to out if that was supplied.
* **Return type:**
  Tensor of [bool](https://docs.python.org/3/library/functions.html#bool)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.signbit(-1.2).execute()
True
>>> mt.signbit(mt.array([1, -2.3, 2.1])).execute()
array([False,  True, False])
```
