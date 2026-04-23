# maxframe.tensor.exp

### maxframe.tensor.exp(x, out=None, where=None, \*\*kwargs)

Calculate the exponential of all elements in the input tensor.

* **Parameters:**
  * **x** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html#ufuncs-kwargs).
* **Returns:**
  **out** – Output tensor, element-wise exponential of x.
* **Return type:**
  Tensor

#### SEE ALSO
[`expm1`](maxframe.tensor.expm1.md#maxframe.tensor.expm1)
: Calculate `exp(x) - 1` for all elements in the array.

[`exp2`](maxframe.tensor.exp2.md#maxframe.tensor.exp2)
: Calculate `2**x` for all elements in the array.

### Notes

The irrational number `e` is also known as Euler’s number.  It is
approximately 2.718281, and is the base of the natural logarithm,
`ln` (this means that, if $x = \ln y = \log_e y$,
then $e^x = y$. For real input, `exp(x)` is always positive.

For complex arguments, `x = a + ib`, we can write
$e^x = e^a e^{ib}$.  The first term, $e^a$, is already
known (it is the real argument, described above).  The second term,
$e^{ib}$, is $\cos b + i \sin b$, a function with
magnitude 1 and a periodic phase.

### References

* <a id='id1'>**[1]**</a> Wikipedia, “Exponential function”, [http://en.wikipedia.org/wiki/Exponential_function](http://en.wikipedia.org/wiki/Exponential_function)
* <a id='id2'>**[2]**</a> M. Abramovitz and I. A. Stegun, “Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables,” Dover, 1964, p. 69, [http://www.math.sfu.ca/~cbm/aands/page_69.htm](http://www.math.sfu.ca/~cbm/aands/page_69.htm)

### Examples

Plot the magnitude and phase of `exp(x)` in the complex plane:

```pycon
>>> import maxframe.tensor as mt
>>> import matplotlib.pyplot as plt
```

```pycon
>>> x = mt.linspace(-2*mt.pi, 2*mt.pi, 100)
>>> xx = x + 1j * x[:, mt.newaxis] # a + ib over complex plane
>>> out = mt.exp(xx)
```

```pycon
>>> plt.subplot(121)
>>> plt.imshow(mt.abs(out).execute(),
...            extent=[-2*mt.pi, 2*mt.pi, -2*mt.pi, 2*mt.pi], cmap='gray')
>>> plt.title('Magnitude of exp(x)')
```

```pycon
>>> plt.subplot(122)
>>> plt.imshow(mt.angle(out).execute(),
...            extent=[-2*mt.pi, 2*mt.pi, -2*mt.pi, 2*mt.pi], cmap='hsv')
>>> plt.title('Phase (angle) of exp(x)')
>>> plt.show()
```
