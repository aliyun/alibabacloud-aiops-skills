# maxframe.tensor.special.dawsn

### maxframe.tensor.special.dawsn(x, out=None, where=None, \*\*kwargs)

Dawson’s integral.

Computes:

```default
exp(-x**2) * integral(exp(t**2), t=0..x).
```

* **Parameters:**
  * **x** (*array_like*) – Function parameter.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **y** – Value of the integral.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`wofz`](maxframe.tensor.special.wofz.md#maxframe.tensor.special.wofz), [`erf`](maxframe.tensor.special.erf.md#maxframe.tensor.special.erf), [`erfc`](maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc), [`erfcx`](maxframe.tensor.special.erfcx.md#maxframe.tensor.special.erfcx), [`erfi`](maxframe.tensor.special.erfi.md#maxframe.tensor.special.erfi)

### References

* <a id='id1'>**[1]**</a> Steven G. Johnson, Faddeeva W function implementation. [http://ab-initio.mit.edu/Faddeeva](http://ab-initio.mit.edu/Faddeeva)
