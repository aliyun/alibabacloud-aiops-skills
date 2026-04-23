# maxframe.tensor.special.wofz

### maxframe.tensor.special.wofz(x, out=None, where=None, \*\*kwargs)

Faddeeva function

Returns the value of the Faddeeva function for complex argument:

```default
exp(-z**2) * erfc(-i*z)
```

* **Parameters:**
  * **z** (*array_like*) – complex argument
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  Value of the Faddeeva function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`dawsn`](maxframe.tensor.special.dawsn.md#maxframe.tensor.special.dawsn), [`erf`](maxframe.tensor.special.erf.md#maxframe.tensor.special.erf), [`erfc`](maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc), [`erfcx`](maxframe.tensor.special.erfcx.md#maxframe.tensor.special.erfcx), [`erfi`](maxframe.tensor.special.erfi.md#maxframe.tensor.special.erfi)

### References

* <a id='id1'>**[1]**</a> Steven G. Johnson, Faddeeva W function implementation. [http://ab-initio.mit.edu/Faddeeva](http://ab-initio.mit.edu/Faddeeva)
