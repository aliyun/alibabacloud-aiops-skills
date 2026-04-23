# maxframe.tensor.tril

### maxframe.tensor.tril(m, k=0, gpu=None)

Lower triangle of a tensor.

Return a copy of a tensor with elements above the k-th diagonal zeroed.

* **Parameters:**
  * **m** (*array_like* *,* *shape* *(**M* *,* *N* *)*) – Input tensor.
  * **k** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Diagonal above which to zero elements.  k = 0 (the default) is the
    main diagonal, k < 0 is below it and k > 0 is above.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, None as default
* **Returns:**
  **tril** – Lower triangle of m, of same shape and data-type as m.
* **Return type:**
  Tensor, shape (M, N)

#### SEE ALSO
[`triu`](maxframe.tensor.triu.md#maxframe.tensor.triu)
: same thing, only for the upper triangle

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.tril([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1).execute()
array([[ 0,  0,  0],
       [ 4,  0,  0],
       [ 7,  8,  0],
       [10, 11, 12]])
```
