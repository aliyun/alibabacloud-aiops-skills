# maxframe.tensor.special.betainc

### maxframe.tensor.special.betainc(a, b, x, out=None, \*\*kwargs)

Regularized incomplete beta function.

Computes the regularized incomplete beta function, defined as <sup>[1](#id2)</sup>:

$$
I_x(a, b) = \frac{\Gamma(a+b)}{\Gamma(a)\Gamma(b)} \int_0^x
t^{a-1}(1-t)^{b-1}dt,
$$

for $0 \leq x \leq 1$.

This function is the cumulative distribution function for the beta
distribution; its range is [0, 1].

* **Parameters:**
  * **a** (*array_like*) – Positive, real-valued parameters
  * **b** (*array_like*) – Positive, real-valued parameters
  * **x** (*array_like*) – Real-valued such that $0 \leq x \leq 1$,
    the upper limit of integration
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Value of the regularized incomplete beta function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`beta`](maxframe.tensor.special.beta.md#maxframe.tensor.special.beta)
: beta function

[`betaincinv`](maxframe.tensor.special.betaincinv.md#maxframe.tensor.special.betaincinv)
: inverse of the regularized incomplete beta function

`betaincc`
: complement of the regularized incomplete beta function

[`scipy.stats.beta`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html#scipy.stats.beta)
: beta distribution

### Notes

The term *regularized* in the name of this function refers to the
scaling of the function by the gamma function terms shown in the
formula.  When not qualified as *regularized*, the name *incomplete
beta function* often refers to just the integral expression,
without the gamma terms.  One can use the function beta from
scipy.special to get this “nonregularized” incomplete beta
function by multiplying the result of `betainc(a, b, x)` by
`beta(a, b)`.

### References

* <a id='id2'>**[1]**</a> NIST Digital Library of Mathematical Functions [https://dlmf.nist.gov/8.17](https://dlmf.nist.gov/8.17)
