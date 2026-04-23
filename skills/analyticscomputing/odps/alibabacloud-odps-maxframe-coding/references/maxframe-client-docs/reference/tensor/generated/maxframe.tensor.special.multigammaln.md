# maxframe.tensor.special.multigammaln

### maxframe.tensor.special.multigammaln(a, b, \*\*kwargs)

Returns the log of multivariate gamma, also sometimes called the
generalized gamma.

* **Parameters:**
  * **a** (*ndarray*) – The multivariate gamma is computed for each item of a.
  * **d** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The dimension of the space of integration.
* **Returns:**
  **res** – The values of the log multivariate gamma at the given points a.
* **Return type:**
  ndarray

### Notes

The formal definition of the multivariate gamma of dimension d for a real
a is

$$
\Gamma_d(a) = \int_{A>0} e^{-tr(A)} |A|^{a - (d+1)/2} dA
$$

with the condition $a > (d-1)/2$, and $A > 0$ being the set of
all the positive definite matrices of dimension d.  Note that a is a
scalar: the integrand only is multivariate, the argument is not (the
function is defined over a subset of the real set).

This can be proven to be equal to the much friendlier equation

$$
\Gamma_d(a) = \pi^{d(d-1)/4} \prod_{i=1}^{d} \Gamma(a - (i-1)/2).
$$

### References

R. J. Muirhead, Aspects of multivariate statistical theory (Wiley Series in
probability and mathematical statistics).
