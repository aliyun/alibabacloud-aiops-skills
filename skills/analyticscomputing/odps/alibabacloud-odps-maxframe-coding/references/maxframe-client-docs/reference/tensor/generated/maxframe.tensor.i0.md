# maxframe.tensor.i0

### maxframe.tensor.i0(x, \*\*kwargs)

Modified Bessel function of the first kind, order 0.

Usually denoted $I_0$.  This function does broadcast, but will *not*
“up-cast” int dtype arguments unless accompanied by at least one float or
complex dtype argument (see Raises below).

* **Parameters:**
  **x** (*array_like* *,* *dtype float* *or* [*complex*](https://docs.python.org/3/library/functions.html#complex)) – Argument of the Bessel function.
* **Returns:**
  **out** – The modified Bessel function evaluated at each of the elements of x.
* **Return type:**
  Tensor, shape = x.shape, dtype = x.dtype
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – array cannot be safely cast to required type: If argument consists exclusively of int dtypes.

#### SEE ALSO
[`scipy.special.iv`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.iv.html#scipy.special.iv), [`scipy.special.ive`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.ive.html#scipy.special.ive)

### Notes

We use the algorithm published by Clenshaw <sup>[1](#id4)</sup> and referenced by
Abramowitz and Stegun <sup>[2](#id5)</sup>, for which the function domain is
partitioned into the two intervals [0,8] and (8,inf), and Chebyshev
polynomial expansions are employed in each interval. Relative error on
the domain [0,30] using IEEE arithmetic is documented <sup>[3](#id6)</sup> as having a
peak of 5.8e-16 with an rms of 1.4e-16 (n = 30000).

### References

* <a id='id4'>**[1]**</a> C. W. Clenshaw, “Chebyshev series for mathematical functions”, in *National Physical Laboratory Mathematical Tables*, vol. 5, London: Her Majesty’s Stationery Office, 1962.
* <a id='id5'>**[2]**</a> M. Abramowitz and I. A. Stegun, *Handbook of Mathematical Functions*, 10th printing, New York: Dover, 1964, pp. 379. [http://www.math.sfu.ca/~cbm/aands/page_379.htm](http://www.math.sfu.ca/~cbm/aands/page_379.htm)
* <a id='id6'>**[3]**</a> [http://kobesearch.cpan.org/htdocs/Math-Cephes/Math/Cephes.html](http://kobesearch.cpan.org/htdocs/Math-Cephes/Math/Cephes.html)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.i0([0.]).execute()
array([1.])
>>> mt.i0([0., 1. + 2j]).execute()
array([ 1.00000000+0.j        ,  0.18785373+0.64616944j])
```
