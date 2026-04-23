# maxframe.tensor.special.erfinv

### maxframe.tensor.special.erfinv(x, out=None, where=None, \*\*kwargs)

Inverse of the error function.

Computes the inverse of the error function.

In the complex domain, there is no unique complex number w satisfying
erf(w)=z. This indicates a true inverse function would be multivalued.
When the domain restricts to the real, -1 < x < 1, there is a unique real
number satisfying erf(erfinv(x)) = x.

* **Parameters:**
  * **y** (*ndarray*) – Argument at which to evaluate. Domain: [-1, 1]
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **erfinv** – The inverse of erf of y, element-wise
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`erf`](maxframe.tensor.special.erf.md#maxframe.tensor.special.erf)
: Error function of a complex argument

[`erfc`](maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc)
: Complementary error function, `1 - erf(x)`

[`erfcinv`](maxframe.tensor.special.erfcinv.md#maxframe.tensor.special.erfcinv)
: Inverse of the complementary error function
