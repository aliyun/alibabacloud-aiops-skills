# maxframe.tensor.matmul

### maxframe.tensor.matmul(a, b, sparse=None, out=None, \*\*kw)

Matrix product of two tensors.

The behavior depends on the arguments in the following way.

- If both arguments are 2-D they are multiplied like conventional
  matrices.
- If either argument is N-D, N > 2, it is treated as a stack of
  matrices residing in the last two indexes and broadcast accordingly.
- If the first argument is 1-D, it is promoted to a matrix by
  prepending a 1 to its dimensions. After matrix multiplication
  the prepended 1 is removed.
- If the second argument is 1-D, it is promoted to a matrix by
  appending a 1 to its dimensions. After matrix multiplication
  the appended 1 is removed.

Multiplication by a scalar is not allowed, use `*` instead. Note that
multiplying a stack of matrices with a vector will result in a stack of
vectors, but matmul will not recognize it as such.

`matmul` differs from `dot` in two important ways.

- Multiplication by scalars is not allowed.
- Stacks of matrices are broadcast together as if the matrices
  were elements.

* **Parameters:**
  * **a** (*array_like*) – First argument.
  * **b** (*array_like*) – Second argument.
  * **out** (*Tensor* *,* *optional*) – Output argument. This must have the exact kind that would be returned
    if it was not used. In particular, it must have the right type,
    and its dtype must be the dtype that would be returned
    for dot(a,b). This is a performance feature. Therefore, if these
    conditions are not met, an exception is raised, instead of attempting
    to be flexible.
* **Returns:**
  **output** – Returns the dot product of a and b.  If a and b are both
  1-D arrays then a scalar is returned; otherwise an array is
  returned.  If out is given, then it is returned.
* **Return type:**
  Tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If the last dimension of a is not the same size as
      the second-to-last dimension of b.
    
      If scalar value is passed.

#### SEE ALSO
[`vdot`](maxframe.tensor.vdot.md#maxframe.tensor.vdot)
: Complex-conjugating dot product.

[`tensordot`](maxframe.tensor.tensordot.md#maxframe.tensor.tensordot)
: Sum products over arbitrary axes.

[`dot`](maxframe.tensor.dot.md#maxframe.tensor.dot)
: alternative matrix product with different broadcasting rules.

### Notes

The matmul function implements the semantics of the @ operator introduced
in Python 3.5 following PEP465.

### Examples

For 2-D arrays it is the matrix product:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = [[1, 0], [0, 1]]
>>> b = [[4, 1], [2, 2]]
>>> mt.matmul(a, b).execute()
array([[4, 1],
       [2, 2]])
```

For 2-D mixed with 1-D, the result is the usual.

```pycon
>>> a = [[1, 0], [0, 1]]
>>> b = [1, 2]
>>> mt.matmul(a, b).execute()
array([1, 2])
>>> mt.matmul(b, a).execute()
array([1, 2])
```

Broadcasting is conventional for stacks of arrays

```pycon
>>> a = mt.arange(2*2*4).reshape((2,2,4))
>>> b = mt.arange(2*2*4).reshape((2,4,2))
>>> mt.matmul(a,b).shape
(2, 2, 2)
>>> mt.matmul(a,b)[0,1,1].execute()
98
>>> mt.sum(a[0,1,:] * b[0,:,1]).execute()
98
```

Vector, vector returns the scalar inner product, but neither argument
is complex-conjugated:

```pycon
>>> mt.matmul([2j, 3j], [2j, 3j]).execute()
(-13+0j)
```

Scalar multiplication raises an error.

```pycon
>>> mt.matmul([1,2], 3)
Traceback (most recent call last):
...
ValueError: Scalar operands are not allowed, use '*' instead
```
