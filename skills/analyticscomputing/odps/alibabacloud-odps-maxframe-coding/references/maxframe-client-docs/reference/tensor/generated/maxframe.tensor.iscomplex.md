# maxframe.tensor.iscomplex

### maxframe.tensor.iscomplex(x, \*\*kwargs)

Returns a bool tensor, where True if input element is complex.

What is tested is whether the input has a non-zero imaginary part, not if
the input type is complex.

* **Parameters:**
  **x** (*array_like*) – Input tensor.
* **Returns:**
  **out** – Output tensor.
* **Return type:**
  Tensor of bools

#### SEE ALSO
[`isreal`](maxframe.tensor.isreal.md#maxframe.tensor.isreal)

`iscomplexobj`
: Return True if x is a complex type or an array of complex numbers.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.iscomplex([1+1j, 1+0j, 4.5, 3, 2, 2j]).execute()
array([ True, False, False, False, False,  True])
```
