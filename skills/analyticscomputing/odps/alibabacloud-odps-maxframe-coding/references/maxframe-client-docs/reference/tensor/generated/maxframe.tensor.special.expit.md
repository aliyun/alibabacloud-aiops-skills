# maxframe.tensor.special.expit

### maxframe.tensor.special.expit(x, out=None)

Expit (a.k.a. logistic sigmoid) ufunc for ndarrays.

The expit function, also known as the logistic sigmoid function, is
defined as `expit(x) = 1/(1+exp(-x))`.  It is the inverse of the
logit function.

* **Parameters:**
  * **x** (*ndarray*) – The ndarray to apply expit to element-wise.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  An ndarray of the same shape as x. Its entries
  are expit of the corresponding entry of x.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`logit`](maxframe.tensor.special.logit.md#maxframe.tensor.special.logit)

### Notes

As a ufunc expit takes a number of optional
keyword arguments. For more information
see [ufuncs](https://docs.scipy.org/doc/numpy/reference/ufuncs.html)
