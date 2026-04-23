# maxframe.tensor.tanh

### maxframe.tensor.tanh(x, out=None, where=None, \*\*kwargs)

Compute hyperbolic tangent element-wise.

Equivalent to `mt.sinh(x)/np.cosh(x)` or `-1j * mt.tan(1j*x)`.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding hyperbolic tangent values.
* **Return type:**
  Tensor

### Notes

If out is provided, the function writes the result into it,
and returns a reference to out.  (See Examples)

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I. A. Stegun, Handbook of Mathematical Functions. New York, NY: Dover, 1972, pg. 83. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Hyperbolic function”, [http://en.wikipedia.org/wiki/Hyperbolic_function](http://en.wikipedia.org/wiki/Hyperbolic_function)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.tanh((0, mt.pi*1j, mt.pi*1j/2)).execute()
array([ 0. +0.00000000e+00j,  0. -1.22460635e-16j,  0. +1.63317787e+16j])
```

```pycon
>>> # Example of providing the optional output parameter illustrating
>>> # that what is returned is a reference to said parameter
>>> out1 = mt.zeros(1)
>>> out2 = mt.tanh([0.1], out1)
>>> out2 is out1
True
```

```pycon
>>> # Example of ValueError due to provision of shape mis-matched `out`
>>> mt.tanh(mt.zeros((3,3)),mt.zeros((2,2)))
Traceback (most recent call last):
...
ValueError: operators could not be broadcast together with shapes (3,3) (2,2)
```
