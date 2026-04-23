# maxframe.tensor.special.kve

### maxframe.tensor.special.kve(v, z, out=None)

Exponentially scaled modified Bessel function of the second kind.

Returns the exponentially scaled, modified Bessel function of the
second kind (sometimes called the third kind) for real order v at
complex z:

```default
kve(v, z) = kv(v, z) * exp(z)
```

* **Parameters:**
  * **v** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float)) – Order of Bessel functions
  * **z** (*array_like* *of* [*complex*](https://docs.python.org/3/library/functions.html#complex)) – Argument at which to evaluate the Bessel functions
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  The exponentially scaled modified Bessel function of the second kind.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`kv`](maxframe.tensor.special.kv.md#maxframe.tensor.special.kv)
: This function without exponential scaling.

`k0e`
: Faster version of this function for order 0.

`k1e`
: Faster version of this function for order 1.

### Notes

Wrapper for AMOS <sup>[1](#id3)</sup> routine zbesk.  For a discussion of the
algorithm used, see <sup>[2](#id4)</sup> and the references therein.

### References

* <a id='id3'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
* <a id='id4'>**[2]**</a> Donald E. Amos, “Algorithm 644: A portable package for Bessel functions of a complex argument and nonnegative order”, ACM TOMS Vol. 12 Issue 3, Sept. 1986, p. 265
