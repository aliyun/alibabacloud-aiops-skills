# maxframe.tensor.swapaxes

### maxframe.tensor.swapaxes(a, axis1, axis2)

Interchange two axes of a tensor.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis1** ([*int*](https://docs.python.org/3/library/functions.html#int)) – First axis.
  * **axis2** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Second axis.
* **Returns:**
  **a_swapped** – If a is a Tensor, then a view of a is
  returned; otherwise a new tensor is created.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[1,2,3]])
>>> mt.swapaxes(x,0,1).execute()
array([[1],
       [2],
       [3]])
```

```pycon
>>> x = mt.array([[[0,1],[2,3]],[[4,5],[6,7]]])
>>> x.execute()
array([[[0, 1],
        [2, 3]],
       [[4, 5],
        [6, 7]]])
```

```pycon
>>> mt.swapaxes(x,0,2).execute()
array([[[0, 4],
        [2, 6]],
       [[1, 5],
        [3, 7]]])
```
