# maxframe.tensor.special.xlogy

### maxframe.tensor.special.xlogy(x1, x2, out=None, where=None, \*\*kwargs)

Compute `x*log(y)` so that the result is 0 if `x = 0`.

* **Parameters:**
  * **x** (*array_like*) – Multiplier
  * **y** (*array_like*) – Argument
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  **z** – Computed x\*log(y)
* **Return type:**
  scalar or ndarray

### Notes

The log function used in the computation is the natural log.
