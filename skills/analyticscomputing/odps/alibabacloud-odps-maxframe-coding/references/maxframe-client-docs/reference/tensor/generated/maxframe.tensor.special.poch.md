# maxframe.tensor.special.poch

### maxframe.tensor.special.poch(a, b, \*\*kwargs)

Pochhammer symbol.

The Pochhammer symbol (rising factorial) is defined as

$$
(z)_m = \frac{\Gamma(z + m)}{\Gamma(z)}
$$

For positive integer m it reads

$$
(z)_m = z (z + 1) ... (z + m - 1)
$$

See [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf) for more details.

* **Parameters:**
  * **z** (*array_like*) – Real-valued arguments.
  * **m** (*array_like*) – Real-valued arguments.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  The value of the function.
* **Return type:**
  scalar or ndarray

### References
