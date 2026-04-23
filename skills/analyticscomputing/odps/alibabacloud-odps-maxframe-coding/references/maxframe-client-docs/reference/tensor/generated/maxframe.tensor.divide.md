# maxframe.tensor.divide

### maxframe.tensor.divide(x1, x2, out=None, where=None, \*\*kwargs)

Divide arguments element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Dividend tensor.
  * **x2** (*array_like*) – Divisor tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – The quotient x1/x2, element-wise. Returns a scalar if both x1 and x2 are scalars.
* **Return type:**
  Tensor

### Notes

Equivalent to x1 / x2 in terms of array-broadcasting.

Behavior on division by zero can be changed using seterr.

In Python 2, when both x1 and x2 are of an integer type, divide will behave like floor_divide.
In Python 3, it behaves like true_divide.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.divide(2.0, 4.0).execute()
0.5
>>> x1 = mt.arange(9.0).reshape((3, 3))
>>> x2 = mt.arange(3.0)
>>> mt.divide(x1, x2).execute()
array([[ NaN,  1. ,  1. ],
       [ Inf,  4. ,  2.5],
       [ Inf,  7. ,  4. ]])
Note the behavior with integer types (Python 2 only):
>>> mt.divide(2, 4).execute()
0
>>> mt.divide(2, 4.).execute()
0.5
Division by zero always yields zero in integer arithmetic (again, Python 2 only),
and does not raise an exception or a warning:
>>> mt.divide(mt.array([0, 1], dtype=int), mt.array([0, 0], dtype=int)).execute()
array([0, 0])
Division by zero can, however, be caught using seterr:
>>> old_err_state = mt.seterr(divide='raise')
>>> mt.divide(1, 0).execute()
Traceback (most recent call last):
...
FloatingPointError: divide by zero encountered in divide
>>> ignored_states = mt.seterr(**old_err_state)
>>> mt.divide(1, 0).execute()
0
```
