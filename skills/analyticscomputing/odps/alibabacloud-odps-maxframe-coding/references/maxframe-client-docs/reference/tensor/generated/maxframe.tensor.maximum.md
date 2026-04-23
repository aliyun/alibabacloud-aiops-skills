# maxframe.tensor.maximum

### maxframe.tensor.maximum(x1, x2, out=None, where=None, \*\*kwargs)

Element-wise maximum of tensor elements.

Compare two tensors and returns a new array containing the element-wise
maxima. If one of the elements being compared is a NaN, then that
element is returned. If both elements are NaNs then the first is
returned. The latter distinction is important for complex NaNs, which
are defined as at least one of the real or imaginary parts being a NaN.
The net effect is that NaNs are propagated.

* **Parameters:**
  * **x1** (*array_like*) – The tensors holding the elements to be compared. They must have
    the same shape, or shapes that can be broadcast to a single shape.
  * **x2** (*array_like*) – The tensors holding the elements to be compared. They must have
    the same shape, or shapes that can be broadcast to a single shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The maximum of x1 and x2, element-wise.  Returns scalar if
  both  x1 and x2 are scalars.
* **Return type:**
  ndarray or scalar

#### SEE ALSO
[`minimum`](maxframe.tensor.minimum.md#maxframe.tensor.minimum)
: Element-wise minimum of two tensors, propagates NaNs.

[`fmax`](maxframe.tensor.fmax.md#maxframe.tensor.fmax)
: Element-wise maximum of two tensors, ignores NaNs.

`amax`
: The maximum value of a tensor along a given axis, propagates NaNs.

[`nanmax`](maxframe.tensor.nanmax.md#maxframe.tensor.nanmax)
: The maximum value of a tensor along a given axis, ignores NaNs.

[`fmin`](maxframe.tensor.fmin.md#maxframe.tensor.fmin), `amin`, [`nanmin`](maxframe.tensor.nanmin.md#maxframe.tensor.nanmin)

### Notes

The maximum is equivalent to `mt.where(x1 >= x2, x1, x2)` when
neither x1 nor x2 are nans, but it is faster and does proper
broadcasting.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.maximum([2, 3, 4], [1, 5, 2]).execute()
array([2, 5, 4])
```

```pycon
>>> mt.maximum(mt.eye(2), [0.5, 2]).execute() # broadcasting
array([[ 1. ,  2. ],
       [ 0.5,  2. ]])
```

```pycon
>>> mt.maximum([mt.nan, 0, mt.nan], [0, mt.nan, mt.nan]).execute()
array([ NaN,  NaN,  NaN])
>>> mt.maximum(mt.Inf, 1).execute()
inf
```
