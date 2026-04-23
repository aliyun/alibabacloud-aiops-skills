# maxframe.tensor.cos

### maxframe.tensor.cos(x, out=None, where=None, \*\*kwargs)

Cosine element-wise.

* **Parameters:**
  * **x** (*array_like*) – Input tensor in radians.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding cosine values.
* **Return type:**
  Tensor

### Notes

If out is provided, the function writes the result into it,
and returns a reference to out.  (See Examples)

### References

M. Abramowitz and I. A. Stegun, Handbook of Mathematical Functions.
New York, NY: Dover, 1972.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.cos(mt.array([0, mt.pi/2, mt.pi])).execute()
array([  1.00000000e+00,   6.12303177e-17,  -1.00000000e+00])
>>>
>>> # Example of providing the optional output parameter
>>> out1 = mt.empty(1)
>>> out2 = mt.cos([0.1], out1)
>>> out2 is out1
True
>>>
>>> # Example of ValueError due to provision of shape mis-matched `out`
>>> mt.cos(mt.zeros((3,3)),mt.zeros((2,2)))
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ValueError: operators could not be broadcast together with shapes (3,3) (2,2)
```
