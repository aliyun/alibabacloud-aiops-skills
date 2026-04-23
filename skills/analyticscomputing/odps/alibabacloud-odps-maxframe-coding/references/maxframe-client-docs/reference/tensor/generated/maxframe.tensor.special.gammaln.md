# maxframe.tensor.special.gammaln

### maxframe.tensor.special.gammaln(x, out=None, where=None, \*\*kwargs)

Logarithm of the absolute value of the Gamma function.

* **Parameters:**
  * **x** (*array-like*) – Values on the real line at which to compute `gammaln`
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **gammaln** – Values of `gammaln` at x.
* **Return type:**
  Tensor

#### SEE ALSO
[`gammasgn`](maxframe.tensor.special.gammasgn.md#maxframe.tensor.special.gammasgn)
: sign of the gamma function

[`loggamma`](maxframe.tensor.special.loggamma.md#maxframe.tensor.special.loggamma)
: principal branch of the logarithm of the gamma function

### Notes

When used in conjunction with gammasgn, this function is useful
for working in logspace on the real axis without having to deal with
complex numbers, via the relation `exp(gammaln(x)) = gammasgn(x)*gamma(x)`.

For complex-valued log-gamma, use loggamma instead of gammaln.
