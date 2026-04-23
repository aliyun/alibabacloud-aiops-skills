# maxframe.tensor.special.ellip_normal

### maxframe.tensor.special.ellip_normal(h2, k2, n, p, \*\*kwargs)

Ellipsoidal harmonic normalization constants gamma^p_n

The normalization constant is defined as

$$
\gamma^p_n=8\int_{0}^{h}dx\int_{h}^{k}dy
\frac{(y^2-x^2)(E^p_n(y)E^p_n(x))^2}{\sqrt((k^2-y^2)(y^2-h^2)(h^2-x^2)(k^2-x^2)}
$$

* **Parameters:**
  * **h2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `h**2`
  * **k2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `k**2`; should be larger than `h**2`
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Degree.
  * **p** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Order, can range between [1,2n+1].
* **Returns:**
  **gamma** – The normalization constant $\gamma^p_n$
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`ellip_harm`](maxframe.tensor.special.ellip_harm.md#maxframe.tensor.special.ellip_harm), [`ellip_harm_2`](maxframe.tensor.special.ellip_harm_2.md#maxframe.tensor.special.ellip_harm_2)
