# maxframe.tensor.special.fresnel

### maxframe.tensor.special.fresnel(x, out=None, \*\*kwargs)

Fresnel integrals.

The Fresnel integrals are defined as

$$
S(z) &= \int_0^z \sin(\pi t^2 /2) dt \\
C(z) &= \int_0^z \cos(\pi t^2 /2) dt.
$$

See [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf) for details.

* **Parameters:**
  * **z** (*array_like*) – Real or complex valued argument
  * **out** (*2-tuple* *of* *ndarrays* *,* *optional*) – Optional output arrays for the function results
* **Returns:**
  **S, C** – Values of the Fresnel integrals
* **Return type:**
  2-tuple of scalar or ndarray

#### SEE ALSO
`fresnel_zeros`
: zeros of the Fresnel integrals

### References
