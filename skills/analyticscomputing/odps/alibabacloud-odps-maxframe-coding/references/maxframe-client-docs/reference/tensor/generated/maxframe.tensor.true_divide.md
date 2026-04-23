# maxframe.tensor.true_divide

### maxframe.tensor.true_divide(x1, x2, out=None, where=None, \*\*kwargs)

Returns a true division of the inputs, element-wise.

Instead of the Python traditional ‘floor division’, this returns a true
division.  True division adjusts the output type to present the best
answer, regardless of input types.

* **Parameters:**
  * **x1** (*array_like*) – Dividend tensor.
  * **x2** (*array_like*) – Divisor tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Result is scalar if both inputs are scalar, tensor otherwise.
* **Return type:**
  Tensor

### Notes

The floor division operator `//` was added in Python 2.2 making
`//` and `/` equivalent operators.  The default floor division
operation of `/` can be replaced by true division with `from
__future__ import division`.

In Python 3.0, `//` is the floor division operator and `/` the
true division operator.  The `true_divide(x1, x2)` function is
equivalent to true division in Python.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(5)
>>> mt.true_divide(x, 4).execute()
array([ 0.  ,  0.25,  0.5 ,  0.75,  1.  ])
```

# for python 2
>>> (x/4).execute()
array([0, 0, 0, 0, 1])
>>> (x//4).execute()
array([0, 0, 0, 0, 1])
