# maxframe.tensor.diag

### maxframe.tensor.diag(v, k=0, sparse=None, gpu=None, chunk_size=None)

Extract a diagonal or construct a diagonal tensor.

See the more detailed documentation for `mt.diagonal` if you use this
function to extract a diagonal and wish to write to the resulting tensor

* **Parameters:**
  * **v** (*array_like*) – If v is a 2-D tensor, return its k-th diagonal.
    If v is a 1-D tensor, return a 2-D tensor with v on the k-th
    diagonal.
  * **k** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Diagonal in question. The default is 0. Use k>0 for diagonals
    above the main diagonal, and k<0 for diagonals below the main
    diagonal.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Create sparse tensor if True, False as default
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **out** – The extracted diagonal or constructed diagonal tensor.
* **Return type:**
  Tensor

#### SEE ALSO
`diagonal`
: Return specified diagonals.

[`diagflat`](maxframe.tensor.diagflat.md#maxframe.tensor.diagflat)
: Create a 2-D array with the flattened input as a diagonal.

[`trace`](https://docs.python.org/3/library/trace.html#module-trace)
: Sum along diagonals.

[`triu`](maxframe.tensor.triu.md#maxframe.tensor.triu)
: Upper triangle of a tensor.

[`tril`](maxframe.tensor.tril.md#maxframe.tensor.tril)
: Lower triangle of a tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(9).reshape((3,3))
>>> x.execute()
array([[0, 1, 2],
       [3, 4, 5],
       [6, 7, 8]])
```

```pycon
>>> mt.diag(x).execute()
array([0, 4, 8])
>>> mt.diag(x, k=1).execute()
array([1, 5])
>>> mt.diag(x, k=-1).execute()
array([3, 7])
```

```pycon
>>> mt.diag(mt.diag(x)).execute()
array([[0, 0, 0],
       [0, 4, 0],
       [0, 0, 8]])
```
