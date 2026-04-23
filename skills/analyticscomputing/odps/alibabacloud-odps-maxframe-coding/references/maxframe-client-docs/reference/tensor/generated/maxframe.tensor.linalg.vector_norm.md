# maxframe.tensor.linalg.vector_norm

### maxframe.tensor.linalg.vector_norm(x, , axis=None, keepdims=False, ord=2)

Computes the vector norm of a vector (or batch of vectors) `x`.

This function is Array API compatible.

* **Parameters:**
  * **x** (*array_like*) – Input array.
  * **axis** ( *{None* *,* [*int*](https://docs.python.org/3/library/functions.html#int) *,* *2-tuple* *of* *ints}* *,* *optional*) – If an integer, `axis` specifies the axis (dimension) along which
    to compute vector norms. If an n-tuple, `axis` specifies the axes
    (dimensions) along which to compute batched vector norms. If `None`,
    the vector norm must be computed over all array values (i.e.,
    equivalent to computing the vector norm of a flattened array).
    Default: `None`.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If this is set to True, the axes which are normed over are left in
    the result as dimensions with size one. Default: False.
  * **ord** ( *{int* *,* [*float*](https://docs.python.org/3/library/functions.html#float) *,* *inf* *,*  *-inf}* *,* *optional*) – The order of the norm. For details see the table under `Notes`
    in numpy.linalg.norm.

#### SEE ALSO
[`numpy.linalg.norm`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html#numpy.linalg.norm)
: Generic norm function

### Examples

```pycon
>>> from numpy import linalg as LA
>>> a = np.arange(9) + 1
>>> a
array([1, 2, 3, 4, 5, 6, 7, 8, 9])
>>> b = a.reshape((3, 3))
>>> b
array([[1, 2, 3],
       [4, 5, 6],
       [7, 8, 9]])
```

```pycon
>>> LA.vector_norm(b)
16.881943016134134
>>> LA.vector_norm(b, ord=np.inf)
9.0
>>> LA.vector_norm(b, ord=-np.inf)
1.0
```

```pycon
>>> LA.vector_norm(b, ord=0)
9.0
>>> LA.vector_norm(b, ord=1)
45.0
>>> LA.vector_norm(b, ord=-1)
0.3534857623790153
>>> LA.vector_norm(b, ord=2)
16.881943016134134
>>> LA.vector_norm(b, ord=-2)
0.8058837395885292
```
