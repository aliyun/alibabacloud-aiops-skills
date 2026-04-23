# maxframe.tensor.special.modfresnelm

### maxframe.tensor.special.modfresnelm(x, out=None)

Modified Fresnel negative integrals

* **Parameters:**
  * **x** (*array_like*) – Function argument
  * **out** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ndarray* *,* *optional*) – Optional output arrays for the function results
* **Returns:**
  * **fm** (*scalar or ndarray*) – Integral `F_-(x)`: `integral(exp(-1j*t*t), t=x..inf)`
  * **km** (*scalar or ndarray*) – Integral `K_-(x)`: `1/sqrt(pi)*exp(1j*(x*x+pi/4))*fp`

#### SEE ALSO
[`modfresnelp`](maxframe.tensor.special.modfresnelp.md#maxframe.tensor.special.modfresnelp)
