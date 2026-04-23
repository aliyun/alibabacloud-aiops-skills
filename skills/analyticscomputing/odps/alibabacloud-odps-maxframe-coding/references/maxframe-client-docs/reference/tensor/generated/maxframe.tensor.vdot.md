# maxframe.tensor.vdot

### maxframe.tensor.vdot(a, b)

Return the dot product of two vectors.

The vdot(a, b) function handles complex numbers differently than
dot(a, b).  If the first argument is complex the complex conjugate
of the first argument is used for the calculation of the dot product.

Note that vdot handles multidimensional tensors differently than dot:
it does *not* perform a matrix product, but flattens input arguments
to 1-D vectors first. Consequently, it should only be used for vectors.

* **Parameters:**
  * **a** (*array_like*) – If a is complex the complex conjugate is taken before calculation
    of the dot product.
  * **b** (*array_like*) – Second argument to the dot product.
* **Returns:**
  **output** – Dot product of a and b.  Can be an int, float, or
  complex depending on the types of a and b.
* **Return type:**
  Tensor

#### SEE ALSO
[`dot`](maxframe.tensor.dot.md#maxframe.tensor.dot)
: Return the dot product without using the complex conjugate of the first argument.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([1+2j,3+4j])
>>> b = mt.array([5+6j,7+8j])
>>> mt.vdot(a, b).execute()
(70-8j)
>>> mt.vdot(b, a).execute()
(70+8j)
```

Note that higher-dimensional arrays are flattened!

```pycon
>>> a = mt.array([[1, 4], [5, 6]])
>>> b = mt.array([[4, 1], [2, 2]])
>>> mt.vdot(a, b).execute()
30
>>> mt.vdot(b, a).execute()
30
>>> 1*4 + 4*1 + 5*2 + 6*2
30
```
