# maxframe.tensor.diagflat

### maxframe.tensor.diagflat(v, k=0, sparse=None, gpu=None, chunk_size=None)

Create a two-dimensional tensor with the flattened input as a diagonal.

* **Parameters:**
  * **v** (*array_like*) – Input data, which is flattened and set as the k-th
    diagonal of the output.
  * **k** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Diagonal to set; 0, the default, corresponds to the “main” diagonal,
    a positive (negative) k giving the number of the diagonal above
    (below) the main.
  * **sparse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Create sparse tensor if True, False as default
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **out** – The 2-D output tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`diag`](maxframe.tensor.diag.md#maxframe.tensor.diag)
: MATLAB work-alike for 1-D and 2-D tensors.

`diagonal`
: Return specified diagonals.

[`trace`](https://docs.python.org/3/library/trace.html#module-trace)
: Sum along diagonals.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.diagflat([[1,2], [3,4]]).execute()
array([[1, 0, 0, 0],
       [0, 2, 0, 0],
       [0, 0, 3, 0],
       [0, 0, 0, 4]])
```

```pycon
>>> mt.diagflat([1,2], 1).execute()
array([[0, 1, 0],
       [0, 0, 2],
       [0, 0, 0]])
```
