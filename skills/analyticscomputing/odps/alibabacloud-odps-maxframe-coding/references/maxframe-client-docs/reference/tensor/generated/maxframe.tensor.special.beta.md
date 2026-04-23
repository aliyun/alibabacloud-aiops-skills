# maxframe.tensor.special.beta

### maxframe.tensor.special.beta(a, b, out=None, \*\*kwargs)

Beta function.

This function is defined in <sup>[1](#id2)</sup> as

$$
B(a, b) = \int_0^1 t^{a-1}(1-t)^{b-1}dt
        = \frac{\Gamma(a)\Gamma(b)}{\Gamma(a+b)},
$$

where $\Gamma$ is the gamma function.

* **Parameters:**
  * **a** (*array_like*) – Real-valued arguments
  * **b** (*array_like*) – Real-valued arguments
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function result
* **Returns:**
  Value of the beta function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gamma`](maxframe.tensor.special.gamma.md#maxframe.tensor.special.gamma)
: the gamma function

[`betainc`](maxframe.tensor.special.betainc.md#maxframe.tensor.special.betainc)
: the regularized incomplete beta function

[`betaln`](maxframe.tensor.special.betaln.md#maxframe.tensor.special.betaln)
: the natural logarithm of the absolute value of the beta function

### References

* <a id='id2'>**[1]**</a> NIST Digital Library of Mathematical Functions, Eq. 5.12.1. [https://dlmf.nist.gov/5.12](https://dlmf.nist.gov/5.12)
