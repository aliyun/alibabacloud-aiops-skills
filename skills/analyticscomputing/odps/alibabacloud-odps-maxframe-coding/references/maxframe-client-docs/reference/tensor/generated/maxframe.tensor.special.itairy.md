# maxframe.tensor.special.itairy

### maxframe.tensor.special.itairy(x, out=None)

Integrals of Airy functions

Calculates the integrals of Airy functions from 0 to x.

* **Parameters:**
  * **x** (*array_like*) – Upper limit of integration (float).
  * **out** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ndarray* *,* *optional*) – Optional output arrays for the function values
* **Returns:**
  * **Apt** (*scalar or ndarray*) – Integral of Ai(t) from 0 to x.
  * **Bpt** (*scalar or ndarray*) – Integral of Bi(t) from 0 to x.
  * **Ant** (*scalar or ndarray*) – Integral of Ai(-t) from 0 to x.
  * **Bnt** (*scalar or ndarray*) – Integral of Bi(-t) from 0 to x.

### Notes

Wrapper for a Fortran routine created by Shanjie Zhang and Jianming
Jin <sup>[1](#id2)</sup>.

### References

* <a id='id2'>**[1]**</a> Zhang, Shanjie and Jin, Jianming. “Computation of Special Functions”, John Wiley and Sons, 1996. [https://people.sc.fsu.edu/~jburkardt/f_src/special_functions/special_functions.html](https://people.sc.fsu.edu/~jburkardt/f_src/special_functions/special_functions.html)
