# maxframe.tensor.fmin

### maxframe.tensor.fmin(x1, x2, out=None, where=None, \*\*kwargs)

Element-wise minimum of array elements.

Compare two tensors and returns a new tensor containing the element-wise
minima. If one of the elements being compared is a NaN, then the
non-nan element is returned. If both elements are NaNs then the first
is returned.  The latter distinction is important for complex NaNs,
which are defined as at least one of the real or imaginary parts being
a NaN. The net effect is that NaNs are ignored when possible.

* **Parameters:**
  * **x1** (*array_like*) – The tensors holding the elements to be compared. They must have
    the same shape.
  * **x2** (*array_like*) – The tensors holding the elements to be compared. They must have
    the same shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The minimum of x1 and x2, element-wise.  Returns scalar if
  both  x1 and x2 are scalars.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`fmax`](maxframe.tensor.fmax.md#maxframe.tensor.fmax)
: Element-wise maximum of two tensors, ignores NaNs.

[`minimum`](maxframe.tensor.minimum.md#maxframe.tensor.minimum)
: Element-wise minimum of two tensors, propagates NaNs.

`amin`
: The minimum value of a tensor along a given axis, propagates NaNs.

[`nanmin`](maxframe.tensor.nanmin.md#maxframe.tensor.nanmin)
: The minimum value of a tensor along a given axis, ignores NaNs.

[`maximum`](maxframe.tensor.maximum.md#maxframe.tensor.maximum), `amax`, [`nanmax`](maxframe.tensor.nanmax.md#maxframe.tensor.nanmax)

### Notes

The fmin is equivalent to `mt.where(x1 <= x2, x1, x2)` when neither
x1 nor x2 are NaNs, but it is faster and does proper broadcasting.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.fmin([2, 3, 4], [1, 5, 2]).execute()
array([1, 3, 2])
```

```pycon
>>> mt.fmin(mt.eye(2), [0.5, 2]).execute()
array([[ 0.5,  0. ],
       [ 0. ,  1. ]])
```

```pycon
>>> mt.fmin([mt.nan, 0, mt.nan],[0, mt.nan, mt.nan]).execute()
array([  0.,   0.,  NaN])
```
