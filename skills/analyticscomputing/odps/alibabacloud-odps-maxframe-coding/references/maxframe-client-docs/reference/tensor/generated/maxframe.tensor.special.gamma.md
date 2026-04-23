# maxframe.tensor.special.gamma

### maxframe.tensor.special.gamma(z, out=None)

gamma function.

The gamma function is defined as

$$
\Gamma(z) = \int_0^\infty t^{z-1} e^{-t} dt
$$

for $\Re(z) > 0$ and is extended to the rest of the complex
plane by analytic continuation. See [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf) for more details.

* **Parameters:**
  * **z** (*array_like*) – Real or complex valued argument
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the gamma function
* **Return type:**
  scalar or ndarray

### Notes

The gamma function is often referred to as the generalized
factorial since $\Gamma(n + 1) = n!$ for natural numbers
$n$. More generally it satisfies the recurrence relation
$\Gamma(z + 1) = z \cdot \Gamma(z)$ for complex $z$,
which, combined with the fact that $\Gamma(1) = 1$, implies
the above identity for $z = n$.

### References
