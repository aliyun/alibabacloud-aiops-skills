# maxframe.tensor.ptp

### maxframe.tensor.ptp(a, axis=None, out=None, keepdims=None)

Range of values (maximum - minimum) along an axis.

The name of the function comes from the acronym for ‘peak to peak’.

* **Parameters:**
  * **a** (*array_like*) – Input values.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which to find the peaks.  By default, flatten the
    array.
  * **out** (*array_like*) – Alternative output tensor in which to place the result. It must
    have the same shape and buffer length as the expected output,
    but the type of the output values will be cast if necessary.
  * **keepdims** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input array.

    If the default value is passed, then keepdims will not be
    passed through to the ptp method of sub-classes of
    Tensor, however any non-default value will be.  If the
    sub-class’ method does not implement keepdims any
    exceptions will be raised.
* **Returns:**
  **ptp** – A new tensor holding the result, unless out was
  specified, in which case a reference to out is returned.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(4).reshape((2,2))
>>> x.execute()
array([[0, 1],
       [2, 3]])
```

```pycon
>>> mt.ptp(x, axis=0).execute()
array([2, 2])
```

```pycon
>>> mt.ptp(x, axis=1).execute()
array([1, 1])
```
