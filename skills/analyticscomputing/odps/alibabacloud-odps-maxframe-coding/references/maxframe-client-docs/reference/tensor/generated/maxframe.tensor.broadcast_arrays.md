# maxframe.tensor.broadcast_arrays

### maxframe.tensor.broadcast_arrays(\*args, \*\*kwargs)

Broadcast any number of arrays against each other.

* **Parameters:**
  **\*args** (*array_likes*) – The tensors to broadcast.
* **Returns:**
  **broadcasted**
* **Return type:**
  [list](https://docs.python.org/3/library/stdtypes.html#list) of tensors

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[1,2,3]])
>>> y = mt.array([[1],[2],[3]])
>>> mt.broadcast_arrays(x, y).execute()
[array([[1, 2, 3],
       [1, 2, 3],
       [1, 2, 3]]), array([[1, 1, 1],
       [2, 2, 2],
       [3, 3, 3]])]
```
