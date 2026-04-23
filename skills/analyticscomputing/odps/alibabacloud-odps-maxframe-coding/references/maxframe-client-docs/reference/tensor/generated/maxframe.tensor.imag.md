# maxframe.tensor.imag

### maxframe.tensor.imag(val, \*\*kwargs)

Return the imaginary part of the complex argument.

* **Parameters:**
  **val** (*array_like*) – Input tensor.
* **Returns:**
  **out** – The imaginary component of the complex argument. If val is real,
  the type of val is used for the output.  If val has complex
  elements, the returned type is float.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`real`](maxframe.tensor.real.md#maxframe.tensor.real), [`angle`](maxframe.tensor.angle.md#maxframe.tensor.angle), `real_if_close`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([1+2j, 3+4j, 5+6j])
>>> a.imag.execute()
array([ 2.,  4.,  6.])
>>> a.imag = mt.array([8, 10, 12])
>>> a.execute()
array([ 1. +8.j,  3.+10.j,  5.+12.j])
>>> mt.imag(1 + 1j).execute()
1.0
```
