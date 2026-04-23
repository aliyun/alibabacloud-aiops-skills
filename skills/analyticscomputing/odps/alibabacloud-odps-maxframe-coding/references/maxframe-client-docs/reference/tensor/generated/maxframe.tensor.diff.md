# maxframe.tensor.diff

### maxframe.tensor.diff(a, n=1, axis=-1)

Calculate the n-th discrete difference along the given axis.

The first difference is given by `out[n] = a[n+1] - a[n]` along
the given axis, higher differences are calculated by using diff
recursively.

* **Parameters:**
  * **a** (*array_like*) – Input tensor
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The number of times values are differenced. If zero, the input
    is returned as-is.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which the difference is taken, default is the
    last axis.
* **Returns:**
  **diff** – The n-th differences. The shape of the output is the same as a
  except along axis where the dimension is smaller by n. The
  type of the output is the same as the type of the difference
  between any two elements of a. This is the same as the type of
  a in most cases. A notable exception is datetime64, which
  results in a timedelta64 output tensor.
* **Return type:**
  Tensor

#### SEE ALSO
`gradient`, [`ediff1d`](maxframe.tensor.ediff1d.md#maxframe.tensor.ediff1d), [`cumsum`](maxframe.tensor.cumsum.md#maxframe.tensor.cumsum)

### Notes

Type is preserved for boolean tensors, so the result will contain
False when consecutive elements are the same and True when they
differ.

For unsigned integer tensors, the results will also be unsigned. This
should not be surprising, as the result is consistent with
calculating the difference directly:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> u8_arr = mt.array([1, 0], dtype=mt.uint8)
>>> mt.diff(u8_arr).execute()
array([255], dtype=uint8)
>>> (u8_arr[1,...] - u8_arr[0,...]).execute()
255
```

If this is not desirable, then the array should be cast to a larger
integer type first:

```pycon
>>> i16_arr = u8_arr.astype(mt.int16)
>>> mt.diff(i16_arr).execute()
array([-1], dtype=int16)
```

### Examples

```pycon
>>> x = mt.array([1, 2, 4, 7, 0])
>>> mt.diff(x).execute()
array([ 1,  2,  3, -7])
>>> mt.diff(x, n=2).execute()
array([  1,   1, -10])
```

```pycon
>>> x = mt.array([[1, 3, 6, 10], [0, 5, 6, 8]])
>>> mt.diff(x).execute()
array([[2, 3, 4],
       [5, 1, 2]])
>>> mt.diff(x, axis=0).execute()
array([[-1,  2,  0, -2]])
```

```pycon
>>> x = mt.arange('1066-10-13', '1066-10-16', dtype=mt.datetime64)
>>> mt.diff(x).execute()
array([1, 1], dtype='timedelta64[D]')
```
