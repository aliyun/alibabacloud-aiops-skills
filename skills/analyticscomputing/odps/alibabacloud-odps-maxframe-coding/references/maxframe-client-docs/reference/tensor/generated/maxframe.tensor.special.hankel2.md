# maxframe.tensor.special.hankel2

### maxframe.tensor.special.hankel2(v, z, out=None)

Hankel function of the second kind

* **Parameters:**
  * **v** (*array_like*) – Order (float).
  * **z** (*array_like*) – Argument (float or complex).
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the Hankel function of the second kind.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`hankel2e`](maxframe.tensor.special.hankel2e.md#maxframe.tensor.special.hankel2e)
: this function with leading exponential behavior stripped off.

### Notes

A wrapper for the AMOS <sup>[1](#id2)</sup> routine zbesh, which carries out the
computation using the relation,

$$
H^{(2)}_v(z) =
-\frac{2}{\imath\pi} \exp(\imath \pi v/2) K_v(z \exp(\imath\pi/2))

$$

where $K_v$ is the modified Bessel function of the second kind.
For negative orders, the relation

$$
H^{(2)}_{-v}(z) = H^{(2)}_v(z) \exp(-\imath\pi v)

$$

is used.

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
