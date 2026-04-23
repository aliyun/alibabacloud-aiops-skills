# maxframe.tensor.special.kv

### maxframe.tensor.special.kv(v, z, out=None)

Modified Bessel function of the second kind of real order v

Returns the modified Bessel function of the second kind for real order
v at complex z.

These are also sometimes called functions of the third kind, Basset
functions, or Macdonald functions.  They are defined as those solutions
of the modified Bessel equation for which,

$$
K_v(x) \sim \sqrt{\pi/(2x)} \exp(-x)

$$

as $x \to \infty$ <sup>[3](#id6)</sup>.

* **Parameters:**
  * **v** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float)) – Order of Bessel functions
  * **z** (*array_like* *of* [*complex*](https://docs.python.org/3/library/functions.html#complex)) – Argument at which to evaluate the Bessel functions
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  The results. Note that input must be of complex type to get complex
  output, e.g. `kv(3, -2+0j)` instead of `kv(3, -2)`.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`kve`](maxframe.tensor.special.kve.md#maxframe.tensor.special.kve)
: This function with leading exponential behavior stripped off.

`kvp`
: Derivative of this function

### Notes

Wrapper for AMOS <sup>[1](#id4)</sup> routine zbesk.  For a discussion of the
algorithm used, see <sup>[2](#id5)</sup> and the references therein.

### References

* <a id='id4'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
* <a id='id5'>**[2]**</a> Donald E. Amos, “Algorithm 644: A portable package for Bessel functions of a complex argument and nonnegative order”, ACM TOMS Vol. 12 Issue 3, Sept. 1986, p. 265
* <a id='id6'>**[3]**</a> NIST Digital Library of Mathematical Functions, Eq. 10.25.E3. [https://dlmf.nist.gov/10.25.E3](https://dlmf.nist.gov/10.25.E3)
