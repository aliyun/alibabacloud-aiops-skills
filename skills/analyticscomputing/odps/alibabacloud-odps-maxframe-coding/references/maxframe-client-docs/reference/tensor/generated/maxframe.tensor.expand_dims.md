# maxframe.tensor.expand_dims

### maxframe.tensor.expand_dims(a, axis)

Expand the shape of a tensor.

Insert a new axis that will appear at the axis position in the expanded
array shape.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Position in the expanded axes where the new axis is placed.
* **Returns:**
  **res** – Output tensor. The number of dimensions is one greater than that of
  the input tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`squeeze`](maxframe.tensor.squeeze.md#maxframe.tensor.squeeze)
: The inverse operation, removing singleton dimensions

[`reshape`](maxframe.tensor.reshape.md#maxframe.tensor.reshape)
: Insert, remove, and combine dimensions, and resize existing ones

`doc.indexing`, [`atleast_1d`](maxframe.tensor.atleast_1d.md#maxframe.tensor.atleast_1d), [`atleast_2d`](maxframe.tensor.atleast_2d.md#maxframe.tensor.atleast_2d), [`atleast_3d`](maxframe.tensor.atleast_3d.md#maxframe.tensor.atleast_3d)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([1,2])
>>> x.shape
(2,)
```

The following is equivalent to `x[mt.newaxis,:]` or `x[mt.newaxis]`:

```pycon
>>> y = mt.expand_dims(x, axis=0)
>>> y.execute()
array([[1, 2]])
>>> y.shape
(1, 2)
```

```pycon
>>> y = mt.expand_dims(x, axis=1)  # Equivalent to x[:,mt.newaxis]
>>> y.execute()
array([[1],
       [2]])
>>> y.shape
(2, 1)
```

Note that some examples may use `None` instead of `np.newaxis`.  These
are the same objects:

```pycon
>>> mt.newaxis is None
True
```
