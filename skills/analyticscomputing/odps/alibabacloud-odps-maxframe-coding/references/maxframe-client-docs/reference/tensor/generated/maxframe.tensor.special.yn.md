# maxframe.tensor.special.yn

### maxframe.tensor.special.yn(n, x, \*\*kwargs)

Bessel function of the second kind of integer order and real argument.

* **Parameters:**
  * **n** (*array_like*) – Order (integer).
  * **x** (*array_like*) – Argument (float).
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  **Y** – Value of the Bessel function, $Y_n(x)$.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`yv`](maxframe.tensor.special.yv.md#maxframe.tensor.special.yv)
: For real order and real or complex argument.

`y0`
: faster implementation of this function for order 0

`y1`
: faster implementation of this function for order 1

### Notes

Wrapper for the Cephes <sup>[1](#id2)</sup> routine yn.

The function is evaluated by forward recurrence on n, starting with
values computed by the Cephes routines y0 and y1. If n = 0 or 1,
the routine for y0 or y1 is called directly.

### References

* <a id='id2'>**[1]**</a> Cephes Mathematical Functions Library, [http://www.netlib.org/cephes/](http://www.netlib.org/cephes/)
