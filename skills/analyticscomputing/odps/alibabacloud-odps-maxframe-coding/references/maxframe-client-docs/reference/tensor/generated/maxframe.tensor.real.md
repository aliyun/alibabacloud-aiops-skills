# maxframe.tensor.real

### maxframe.tensor.real(val, \*\*kwargs)

Return the real part of the complex argument.

* **Parameters:**
  **val** (*array_like*) – Input tensor.
* **Returns:**
  **out** – The real component of the complex argument. If val is real, the type
  of val is used for the output.  If val has complex elements, the
  returned type is float.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
`real_if_close`, [`imag`](maxframe.tensor.imag.md#maxframe.tensor.imag), [`angle`](maxframe.tensor.angle.md#maxframe.tensor.angle)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([1+2j, 3+4j, 5+6j])
>>> a.real.execute()
array([ 1.,  3.,  5.])
>>> a.real = 9
>>> a.execute()
array([ 9.+2.j,  9.+4.j,  9.+6.j])
>>> a.real = mt.array([9, 8, 7])
>>> a.execute()
array([ 9.+2.j,  8.+4.j,  7.+6.j])
>>> mt.real(1 + 1j).execute()
1.0
```
