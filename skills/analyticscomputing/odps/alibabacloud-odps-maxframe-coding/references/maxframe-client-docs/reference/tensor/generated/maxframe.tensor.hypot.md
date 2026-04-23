# maxframe.tensor.hypot

### maxframe.tensor.hypot(x1, x2, out=None, where=None, \*\*kwargs)

Given the “legs” of a right triangle, return its hypotenuse.

Equivalent to `sqrt(x1**2 + x2**2)`, element-wise.  If x1 or
x2 is scalar_like (i.e., unambiguously cast-able to a scalar type),
it is broadcast for use with each element of the other argument.
(See Examples)

* **Parameters:**
  * **x1** (*array_like*) – Leg of the triangle(s).
  * **x2** (*array_like*) – Leg of the triangle(s).
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated array is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **z** – The hypotenuse of the triangle(s).
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.hypot(3*mt.ones((3, 3)), 4*mt.ones((3, 3))).execute()
array([[ 5.,  5.,  5.],
       [ 5.,  5.,  5.],
       [ 5.,  5.,  5.]])
```

Example showing broadcast of scalar_like argument:

```pycon
>>> mt.hypot(3*mt.ones((3, 3)), [4]).execute()
array([[ 5.,  5.,  5.],
       [ 5.,  5.,  5.],
       [ 5.,  5.,  5.]])
```
