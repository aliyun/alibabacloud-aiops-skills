# maxframe.tensor.cumprod

### maxframe.tensor.cumprod(a, axis=None, dtype=None, out=None)

Return the cumulative product of elements along a given axis.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis along which the cumulative product is computed.  By default
    the input is flattened.
  * **dtype** (*dtype* *,* *optional*) – Type of the returned tensor, as well as of the accumulator in which
    the elements are multiplied.  If *dtype* is not specified, it
    defaults to the dtype of a, unless a has an integer dtype with
    a precision less than that of the default platform integer.  In
    that case, the default platform integer is used instead.
  * **out** (*Tensor* *,* *optional*) – Alternative output tensor in which to place the result. It must
    have the same shape and buffer length as the expected output
    but the type of the resulting values will be cast if necessary.
* **Returns:**
  **cumprod** – A new tensor holding the result is returned unless out is
  specified, in which case a reference to out is returned.
* **Return type:**
  Tensor

#### SEE ALSO
`numpy.doc.ufuncs`
: Section “Output arguments”

### Notes

Arithmetic is modular when using integer types, and no error is
raised on overflow.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([1,2,3])
>>> mt.cumprod(a).execute() # intermediate results 1, 1*2
...                         # total product 1*2*3 = 6
array([1, 2, 6])
>>> a = mt.array([[1, 2, 3], [4, 5, 6]])
>>> mt.cumprod(a, dtype=float).execute() # specify type of output
array([   1.,    2.,    6.,   24.,  120.,  720.])
```

The cumulative product for each column (i.e., over the rows) of a:

```pycon
>>> mt.cumprod(a, axis=0).execute()
array([[ 1,  2,  3],
       [ 4, 10, 18]])
```

The cumulative product for each row (i.e. over the columns) of a:

```pycon
>>> mt.cumprod(a,axis=1).execute()
array([[  1,   2,   6],
       [  4,  20, 120]])
```
