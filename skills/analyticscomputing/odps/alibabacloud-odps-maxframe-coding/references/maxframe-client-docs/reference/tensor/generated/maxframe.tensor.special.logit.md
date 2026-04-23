# maxframe.tensor.special.logit

### maxframe.tensor.special.logit(x, \*\*kwargs)

“””
logit(x, out=None)

Logit ufunc for ndarrays.

The logit function is defined as logit(p) = log(p/(1-p)).
Note that logit(0) = -inf, logit(1) = inf, and logit(p)
for p<0 or p>1 yields nan.

* **Parameters:**
  * **x** (*ndarray*) – The ndarray to apply logit to element-wise.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  An ndarray of the same shape as x. Its entries
  are logit of the corresponding entry of x.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`expit`](maxframe.tensor.special.expit.md#maxframe.tensor.special.expit)

### Notes

As a ufunc logit takes a number of optional
keyword arguments. For more information
see [ufuncs](https://docs.scipy.org/doc/numpy/reference/ufuncs.html)
