# maxframe.tensor.logaddexp

### maxframe.tensor.logaddexp(x1, x2, out=None, where=None, \*\*kwargs)

Logarithm of the sum of exponentiations of the inputs.

Calculates `log(exp(x1) + exp(x2))`. This function is useful in
statistics where the calculated probabilities of events may be so small
as to exceed the range of normal floating point numbers.  In such cases
the logarithm of the calculated probability is stored. This function
allows adding probabilities stored in such a fashion.

* **Parameters:**
  * **x1** (*array_like*) – Input values.
  * **x2** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html#ufuncs-kwargs).
* **Returns:**
  **result** – Logarithm of `exp(x1) + exp(x2)`.
* **Return type:**
  Tensor

#### SEE ALSO
[`logaddexp2`](maxframe.tensor.logaddexp2.md#maxframe.tensor.logaddexp2)
: Logarithm of the sum of exponentiations of inputs in base 2.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> prob1 = mt.log(1e-50)
>>> prob2 = mt.log(2.5e-50)
>>> prob12 = mt.logaddexp(prob1, prob2)
>>> prob12.execute()
-113.87649168120691
>>> mt.exp(prob12).execute()
3.5000000000000057e-50
```
