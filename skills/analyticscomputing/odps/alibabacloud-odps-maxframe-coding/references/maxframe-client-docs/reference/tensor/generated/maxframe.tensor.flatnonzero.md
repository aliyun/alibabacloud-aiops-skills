# maxframe.tensor.flatnonzero

### maxframe.tensor.flatnonzero(a)

Return indices that are non-zero in the flattened version of a.

This is equivalent to a.ravel().nonzero()[0].

* **Parameters:**
  **a** (*Tensor*) – Input tensor.
* **Returns:**
  **res** – Output tensor, containing the indices of the elements of a.ravel()
  that are non-zero.
* **Return type:**
  Tensor

#### SEE ALSO
[`nonzero`](maxframe.tensor.nonzero.md#maxframe.tensor.nonzero)
: Return the indices of the non-zero elements of the input tensor.

[`ravel`](maxframe.tensor.ravel.md#maxframe.tensor.ravel)
: Return a 1-D tensor containing the elements of the input tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(-2, 3)
>>> x.execute()
array([-2, -1,  0,  1,  2])
>>> mt.flatnonzero(x).execute()
array([0, 1, 3, 4])
```

Use the indices of the non-zero elements as an index array to extract
these elements:

```pycon
>>> x.ravel()[mt.flatnonzero(x)].execute()
```
