# maxframe.tensor.special.ellip_harm_2

### maxframe.tensor.special.ellip_harm_2(h2, k2, n, p, s, \*\*kwargs)

Ellipsoidal harmonic functions F^p_n(l)

These are also known as Lame functions of the second kind, and are
solutions to the Lame equation:

$$
(s^2 - h^2)(s^2 - k^2)F''(s)
+ s(2s^2 - h^2 - k^2)F'(s) + (a - q s^2)F(s) = 0

$$

where $q = (n+1)n$ and $a$ is the eigenvalue (not
returned) corresponding to the solutions.

* **Parameters:**
  * **h2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `h**2`
  * **k2** ([*float*](https://docs.python.org/3/library/functions.html#float)) – `k**2`; should be larger than `h**2`
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Degree.
  * **p** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Order, can range between [1,2n+1].
  * **s** ([*float*](https://docs.python.org/3/library/functions.html#float)) – Coordinate
* **Returns:**
  **F** – The harmonic $F^p_n(s)$
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`ellip_harm`](maxframe.tensor.special.ellip_harm.md#maxframe.tensor.special.ellip_harm), [`ellip_normal`](maxframe.tensor.special.ellip_normal.md#maxframe.tensor.special.ellip_normal)

### Notes

Lame functions of the second kind are related to the functions of the first kind:

$$
F^p_n(s)=(2n + 1)E^p_n(s)\int_{0}^{1/s}
\frac{du}{(E^p_n(1/u))^2\sqrt{(1-u^2k^2)(1-u^2h^2)}}
$$
