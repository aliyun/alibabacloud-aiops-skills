# maxframe.tensor.tile

### maxframe.tensor.tile(A, reps)

Construct a tensor by repeating A the number of times given by reps.

If reps has length `d`, the result will have dimension of
`max(d, A.ndim)`.

If `A.ndim < d`, A is promoted to be d-dimensional by prepending new
axes. So a shape (3,) array is promoted to (1, 3) for 2-D replication,
or shape (1, 1, 3) for 3-D replication. If this is not the desired
behavior, promote A to d-dimensions manually before calling this
function.

If `A.ndim > d`, reps is promoted to A.ndim by prepending 1’s to it.
Thus for an A of shape (2, 3, 4, 5), a reps of (2, 2) is treated as
(1, 1, 2, 2).

Note : Although tile may be used for broadcasting, it is strongly
recommended to use MaxFrame’s broadcasting operations and functions.

* **Parameters:**
  * **A** (*array_like*) – The input tensor.
  * **reps** (*array_like*) – The number of repetitions of A along each axis.
* **Returns:**
  **c** – The tiled output tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`repeat`](maxframe.tensor.repeat.md#maxframe.tensor.repeat)
: Repeat elements of a tensor.

[`broadcast_to`](maxframe.tensor.broadcast_to.md#maxframe.tensor.broadcast_to)
: Broadcast a tensor to a new shape

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([0, 1, 2])
>>> mt.tile(a, 2).execute()
array([0, 1, 2, 0, 1, 2])
>>> mt.tile(a, (2, 2)).execute()
array([[0, 1, 2, 0, 1, 2],
       [0, 1, 2, 0, 1, 2]])
>>> mt.tile(a, (2, 1, 2)).execute()
array([[[0, 1, 2, 0, 1, 2]],
       [[0, 1, 2, 0, 1, 2]]])
```

```pycon
>>> b = mt.array([[1, 2], [3, 4]])
>>> mt.tile(b, 2).execute()
array([[1, 2, 1, 2],
       [3, 4, 3, 4]])
>>> mt.tile(b, (2, 1)).execute()
array([[1, 2],
       [3, 4],
       [1, 2],
       [3, 4]])
```

```pycon
>>> c = mt.array([1,2,3,4])
>>> mt.tile(c,(4,1)).execute()
array([[1, 2, 3, 4],
       [1, 2, 3, 4],
       [1, 2, 3, 4],
       [1, 2, 3, 4]])
```
