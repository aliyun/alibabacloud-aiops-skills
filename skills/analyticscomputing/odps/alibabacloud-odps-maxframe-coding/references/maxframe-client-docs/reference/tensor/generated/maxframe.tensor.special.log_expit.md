# maxframe.tensor.special.log_expit

### maxframe.tensor.special.log_expit(x, out=None)

Logarithm of the logistic sigmoid function.

The SciPy implementation of the logistic sigmoid function is
scipy.special.expit, so this function is called `log_expit`.

The function is mathematically equivalent to `log(expit(x))`, but
is formulated to avoid loss of precision for inputs with large
(positive or negative) magnitude.

* **Parameters:**
  * **x** (*array_like*) – The values to apply `log_expit` to element-wise.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  **out** – The computed values, an ndarray of the same shape as `x`.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`expit`](maxframe.tensor.special.expit.md#maxframe.tensor.special.expit)

### Notes

As a ufunc, `log_expit` takes a number of optional keyword arguments.
For more information see
[ufuncs](https://docs.scipy.org/doc/numpy/reference/ufuncs.html)
