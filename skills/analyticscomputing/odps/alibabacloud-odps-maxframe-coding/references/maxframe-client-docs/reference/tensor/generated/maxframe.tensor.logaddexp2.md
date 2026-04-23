# maxframe.tensor.logaddexp2

### maxframe.tensor.logaddexp2(x1, x2, out=None, where=None, \*\*kwargs)

Logarithm of the sum of exponentiations of the inputs in base-2.

Calculates `log2(2**x1 + 2**x2)`. This function is useful in machine
learning when the calculated probabilities of events may be so small as
to exceed the range of normal floating point numbers.  In such cases
the base-2 logarithm of the calculated probability can be used instead.
This function allows adding probabilities stored in such a fashion.

* **Parameters:**
  * **x1** (*array_like*) – Input values.
  * **x2** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **result** – Base-2 logarithm of `2**x1 + 2**x2`.
* **Return type:**
  Tensor

#### SEE ALSO
[`logaddexp`](maxframe.tensor.logaddexp.md#maxframe.tensor.logaddexp)
: Logarithm of the sum of exponentiations of the inputs.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> prob1 = mt.log2(1e-50)
>>> prob2 = mt.log2(2.5e-50)
>>> prob12 = mt.logaddexp2(prob1, prob2)
>>> prob1.execute(), prob2.execute(), prob12.execute()
(-166.09640474436813, -164.77447664948076, -164.28904982231052)
>>> (2**prob12).execute()
3.4999999999999914e-50
```
