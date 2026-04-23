# maxframe.tensor.shape

### maxframe.tensor.shape(a)

Return the shape of a tensor.

* **Parameters:**
  **a** (*array_like*) – Input tensor.
* **Returns:**
  **shape** – The elements of the shape tuple give the lengths of the
  corresponding array dimensions.
* **Return type:**
  ExecutableTuple of tensors

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.shape(mt.eye(3)).execute()
(3, 3)
>>> mt.shape([[1, 2]]).execute()
(1, 2)
>>> mt.shape([0]).execute()
(1,)
>>> mt.shape(0).execute()
()
```

```pycon
>>> a = mt.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
>>> mt.shape(a).execute()
(2,)
```
