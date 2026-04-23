# maxframe.tensor.special.jve

### maxframe.tensor.special.jve(v, z, out=None)

Exponentially scaled Bessel function of the first kind of order v.

Defined as:

```default
jve(v, z) = jv(v, z) * exp(-abs(z.imag))
```

* **Parameters:**
  * **v** (*array_like*) – Order (float).
  * **z** (*array_like*) – Argument (float or complex).
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **J** – Value of the exponentially scaled Bessel function.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`jv`](maxframe.tensor.special.jv.md#maxframe.tensor.special.jv)
: Unscaled Bessel function of the first kind

### Notes

For positive v values, the computation is carried out using the AMOS
<sup>[1](#id2)</sup> zbesj routine, which exploits the connection to the modified
Bessel function $I_v$,

$$
J_v(z) = \exp(v\pi\imath/2) I_v(-\imath z)\qquad (\Im z > 0)

J_v(z) = \exp(-v\pi\imath/2) I_v(\imath z)\qquad (\Im z < 0)
$$

For negative v values the formula,

$$
J_{-v}(z) = J_v(z) \cos(\pi v) - Y_v(z) \sin(\pi v)

$$

is used, where $Y_v(z)$ is the Bessel function of the second
kind, computed using the AMOS routine zbesy.  Note that the second
term is exactly zero for integer v; to improve accuracy the second
term is explicitly omitted for v values such that v = floor(v).

Exponentially scaled Bessel functions are useful for large arguments z:
for these, the unscaled Bessel functions can easily under-or overflow.

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
