# maxframe.tensor.reciprocal

### maxframe.tensor.reciprocal(x, out=None, where=None, \*\*kwargs)

Return the reciprocal of the argument, element-wise.

Calculates `1/x`.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Return tensor.
* **Return type:**
  Tensor

### Notes

#### NOTE
This function is not designed to work with integers.

For integer arguments with absolute value larger than 1 the result is
always zero because of the way Python handles integer division.  For
integer zero the result is an overflow.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.reciprocal(2.).execute()
0.5
>>> mt.reciprocal([1, 2., 3.33]).execute()
array([ 1.       ,  0.5      ,  0.3003003])
```
