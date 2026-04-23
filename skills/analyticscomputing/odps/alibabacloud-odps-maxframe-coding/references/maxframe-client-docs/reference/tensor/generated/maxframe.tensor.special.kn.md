# maxframe.tensor.special.kn

### maxframe.tensor.special.kn(n, x, \*\*kwargs)

Modified Bessel function of the second kind of integer order n

Returns the modified Bessel function of the second kind for integer order
n at real z.

These are also sometimes called functions of the third kind, Basset
functions, or Macdonald functions.

* **Parameters:**
  * **n** (*array_like* *of* [*int*](https://docs.python.org/3/library/functions.html#int)) – Order of Bessel functions (floats will truncate with a warning)
  * **x** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float)) – Argument at which to evaluate the Bessel functions
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results.
* **Returns:**
  Value of the Modified Bessel function of the second kind,
  $K_n(x)$.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`kv`](maxframe.tensor.special.kv.md#maxframe.tensor.special.kv)
: Same function, but accepts real order and complex argument

`kvp`
: Derivative of this function

### Notes

Wrapper for AMOS <sup>[1](#id3)</sup> routine zbesk.  For a discussion of the
algorithm used, see <sup>[2](#id4)</sup> and the references therein.

### References

* <a id='id3'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
* <a id='id4'>**[2]**</a> Donald E. Amos, “Algorithm 644: A portable package for Bessel functions of a complex argument and nonnegative order”, ACM TOMS Vol. 12 Issue 3, Sept. 1986, p. 265
