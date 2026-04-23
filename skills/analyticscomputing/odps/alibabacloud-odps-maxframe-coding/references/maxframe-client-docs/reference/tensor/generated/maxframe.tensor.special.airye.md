# maxframe.tensor.special.airye

### maxframe.tensor.special.airye(z, out=None)

Exponentially scaled Airy functions and their derivatives.

Scaling:

```default
eAi  = Ai  * exp(2.0/3.0*z*sqrt(z))
eAip = Aip * exp(2.0/3.0*z*sqrt(z))
eBi  = Bi  * exp(-abs(2.0/3.0*(z*sqrt(z)).real))
eBip = Bip * exp(-abs(2.0/3.0*(z*sqrt(z)).real))
```

* **Parameters:**
  * **z** (*array_like*) – Real or complex argument.
  * **out** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ndarray* *,* *optional*) – Optional output arrays for the function values
* **Returns:**
  **eAi, eAip, eBi, eBip** – Exponentially scaled Airy functions eAi and eBi, and their derivatives
  eAip and eBip
* **Return type:**
  4-tuple of scalar or ndarray

#### SEE ALSO
[`airy`](maxframe.tensor.special.airy.md#maxframe.tensor.special.airy)

### Notes

Wrapper for the AMOS <sup>[1](#id2)</sup> routines zairy and zbiry.

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
