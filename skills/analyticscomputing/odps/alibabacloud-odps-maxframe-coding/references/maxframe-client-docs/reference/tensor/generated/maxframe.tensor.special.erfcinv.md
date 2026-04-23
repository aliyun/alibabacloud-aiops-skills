# maxframe.tensor.special.erfcinv

### maxframe.tensor.special.erfcinv(x, out=None, where=None, \*\*kwargs)

Inverse of the complementary error function.

Computes the inverse of the complementary error function.

In the complex domain, there is no unique complex number w satisfying
erfc(w)=z. This indicates a true inverse function would be multivalued.
When the domain restricts to the real, 0 < x < 2, there is a unique real
number satisfying erfc(erfcinv(x)) = erfcinv(erfc(x)).

It is related to inverse of the error function by erfcinv(1-x) = erfinv(x)

* **Parameters:**
  * **y** (*ndarray*) – Argument at which to evaluate. Domain: [0, 2]
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **erfcinv** – The inverse of erfc of y, element-wise
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`erf`](maxframe.tensor.special.erf.md#maxframe.tensor.special.erf)
: Error function of a complex argument

[`erfc`](maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc)
: Complementary error function, `1 - erf(x)`

[`erfinv`](maxframe.tensor.special.erfinv.md#maxframe.tensor.special.erfinv)
: Inverse of the error function
