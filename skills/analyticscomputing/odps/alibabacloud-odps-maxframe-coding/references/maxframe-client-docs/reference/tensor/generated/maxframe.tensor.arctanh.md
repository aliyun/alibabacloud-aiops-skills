# maxframe.tensor.arctanh

### maxframe.tensor.arctanh(x, out=None, where=None, \*\*kwargs)

Inverse hyperbolic tangent element-wise.

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
  **out** – Array of the same shape as x.
* **Return type:**
  Tensor

### Notes

arctanh is a multivalued function: for each x there are infinitely
many numbers z such that tanh(z) = x. The convention is to return
the z whose imaginary part lies in [-pi/2, pi/2].

For real-valued input data types, arctanh always returns real output.
For each value that cannot be expressed as a real number or infinity,
it yields `nan` and sets the invalid floating point error flag.

For complex-valued input, arctanh is a complex analytical function
that has branch cuts [-1, -inf] and [1, inf] and is continuous from
above on the former and from below on the latter.

The inverse hyperbolic tangent is also known as atanh or `tanh^-1`.

### References

* <a id='id1'>**[1]**</a> M. Abramowitz and I.A. Stegun, “Handbook of Mathematical Functions”, 10th printing, 1964, pp. 86. [http://www.math.sfu.ca/~cbm/aands/](http://www.math.sfu.ca/~cbm/aands/)
* <a id='id2'>**[2]**</a> Wikipedia, “Inverse hyperbolic function”, [http://en.wikipedia.org/wiki/Arctanh](http://en.wikipedia.org/wiki/Arctanh)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.arctanh([0, -0.5]).execute()
array([ 0.        , -0.54930614])
```
