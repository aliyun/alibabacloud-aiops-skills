# maxframe.tensor.sign

### maxframe.tensor.sign(x, out=None, where=None, \*\*kwargs)

Returns an element-wise indication of the sign of a number.

The sign function returns `-1 if x < 0, 0 if x==0, 1 if x > 0`.  nan
is returned for nan inputs.

For complex inputs, the sign function returns
`sign(x.real) + 0j if x.real != 0 else sign(x.imag) + 0j`.

complex(nan, 0) is returned for complex nan inputs.

* **Parameters:**
  * **x** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The sign of x.
* **Return type:**
  Tensor

### Notes

There is more than one definition of sign in common use for complex
numbers.  The definition used here is equivalent to $x/\sqrt{x*x}$
which is different from a common alternative, $x/|x|$.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.sign([-5., 4.5]).execute()
array([-1.,  1.])
>>> mt.sign(0).execute()
0
>>> mt.sign(5-2j).execute()
(1+0j)
```
