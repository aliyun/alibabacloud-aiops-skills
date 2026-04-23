# maxframe.tensor.radians

### maxframe.tensor.radians(x, out=None, where=None, \*\*kwargs)

Convert angles from degrees to radians.

* **Parameters:**
  * **x** (*array_like*) – Input tensor in degrees.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding radian values.
* **Return type:**
  Tensor

#### SEE ALSO
[`deg2rad`](maxframe.tensor.deg2rad.md#maxframe.tensor.deg2rad)
: equivalent function

### Examples

Convert a degree array to radians

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> deg = mt.arange(12.) * 30.
>>> mt.radians(deg).execute()
array([ 0.        ,  0.52359878,  1.04719755,  1.57079633,  2.0943951 ,
        2.61799388,  3.14159265,  3.66519143,  4.1887902 ,  4.71238898,
        5.23598776,  5.75958653])
```

```pycon
>>> out = mt.zeros((deg.shape))
>>> ret = mt.radians(deg, out)
>>> ret is out
True
```
