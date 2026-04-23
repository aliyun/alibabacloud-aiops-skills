# maxframe.tensor.isreal

### maxframe.tensor.isreal(x, \*\*kwargs)

Returns a bool tensor, where True if input element is real.

If element has complex type with zero complex part, the return value
for that element is True.

* **Parameters:**
  **x** (*array_like*) – Input tensor.
* **Returns:**
  **out** – Boolean tensor of same shape as x.
* **Return type:**
  Tensor, [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`iscomplex`](maxframe.tensor.iscomplex.md#maxframe.tensor.iscomplex)

`isrealobj`
: Return True if x is not a complex type.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.isreal([1+1j, 1+0j, 4.5, 3, 2, 2j]).execute()
array([False,  True,  True,  True,  True, False])
```
