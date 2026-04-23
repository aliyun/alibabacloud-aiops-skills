# maxframe.tensor.dot

### maxframe.tensor.dot(a, b, out=None, sparse=None)

Dot product of two arrays. Specifically,

- If both a and b are 1-D arrays, it is inner product of vectors
  (without complex conjugation).
- If both a and b are 2-D arrays, it is matrix multiplication,
  but using [`matmul()`](maxframe.tensor.matmul.md#maxframe.tensor.matmul) or `a @ b` is preferred.
- If either a or b is 0-D (scalar), it is equivalent to [`multiply()`](maxframe.tensor.multiply.md#maxframe.tensor.multiply)
  and using `numpy.multiply(a, b)` or `a * b` is preferred.
- If a is an N-D array and b is a 1-D array, it is a sum product over
  the last axis of a and b.
- If a is an N-D array and b is an M-D array (where `M>=2`), it is a
  sum product over the last axis of a and the second-to-last axis of b:
  ```default
  dot(a, b)[i,j,k,m] = sum(a[i,j,:] * b[k,:,m])
  ```

* **Parameters:**
  * **a** (*array_like*) – First argument.
  * **b** (*array_like*) – Second argument.
  * **out** (*Tensor* *,* *optional*) – Output argument. This must have the exact kind that would be returned
    if it was not used. In particular, it must have the right type, must be
    C-contiguous, and its dtype must be the dtype that would be returned
    for dot(a,b). This is a performance feature. Therefore, if these
    conditions are not met, an exception is raised, instead of attempting
    to be flexible.
* **Returns:**
  **output** – Returns the dot product of a and b.  If a and b are both
  scalars or both 1-D arrays then a scalar is returned; otherwise
  a tensor is returned.
  If out is given, then it is returned.
* **Return type:**
  Tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If the last dimension of a is not the same size as
      the second-to-last dimension of b.

#### SEE ALSO
[`vdot`](maxframe.tensor.vdot.md#maxframe.tensor.vdot)
: Complex-conjugating dot product.

[`tensordot`](maxframe.tensor.tensordot.md#maxframe.tensor.tensordot)
: Sum products over arbitrary axes.

[`einsum`](maxframe.tensor.einsum.md#maxframe.tensor.einsum)
: Einstein summation convention.

[`matmul`](maxframe.tensor.matmul.md#maxframe.tensor.matmul)
: ‘@’ operator as method with out parameter.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.dot(3, 4).execute()
12
```

Neither argument is complex-conjugated:

```pycon
>>> mt.dot([2j, 3j], [2j, 3j]).execute()
(-13+0j)
```

For 2-D arrays it is the matrix product:

```pycon
>>> a = [[1, 0], [0, 1]]
>>> b = [[4, 1], [2, 2]]
>>> mt.dot(a, b).execute()
array([[4, 1],
       [2, 2]])
```

```pycon
>>> a = mt.arange(3*4*5*6).reshape((3,4,5,6))
>>> b = mt.arange(3*4*5*6)[::-1].reshape((5,4,6,3))
>>> mt.dot(a, b)[2,3,2,1,2,2].execute()
499128
>>> mt.sum(a[2,3,2,:] * b[1,2,:,2]).execute()
499128
```
