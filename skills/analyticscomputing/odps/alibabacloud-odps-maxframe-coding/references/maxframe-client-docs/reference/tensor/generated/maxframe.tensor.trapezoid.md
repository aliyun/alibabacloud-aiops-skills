# maxframe.tensor.trapezoid

### maxframe.tensor.trapezoid(y, x=None, dx=1.0, axis=-1)

Integrate along the given axis using the composite trapezoidal rule.

Integrate y (x) along given axis.

* **Parameters:**
  * **y** (*array_like*) – Input tensor to integrate.
  * **x** (*array_like* *,* *optional*) – The sample points corresponding to the y values. If x is None,
    the sample points are assumed to be evenly spaced dx apart. The
    default is None.
  * **dx** (*scalar* *,* *optional*) – The spacing between sample points when x is None. The default is 1.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The axis along which to integrate.
* **Returns:**
  **trapezoid** – Definite integral as approximated by trapezoidal rule.
* **Return type:**
  [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
[`sum`](maxframe.tensor.sum.md#maxframe.tensor.sum), [`cumsum`](maxframe.tensor.cumsum.md#maxframe.tensor.cumsum)

### Notes

Image <sup>[2](#id3)</sup> illustrates trapezoidal rule – y-axis locations of points
will be taken from y tensor, by default x-axis distances between
points will be 1.0, alternatively they can be provided with x tensor
or with dx scalar.  Return value will be equal to combined area under
the red lines.

### References

* <a id='id2'>**[1]**</a> Wikipedia page: [https://en.wikipedia.org/wiki/Trapezoidal_rule](https://en.wikipedia.org/wiki/Trapezoidal_rule)
* <a id='id3'>**[2]**</a> Illustration image: [https://en.wikipedia.org/wiki/File:Composite_trapezoidal_rule_illustration.png](https://en.wikipedia.org/wiki/File:Composite_trapezoidal_rule_illustration.png)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.trapezoid([1,2,3]).execute()
4.0
>>> mt.trapezoid([1,2,3], x=[4,6,8]).execute()
8.0
>>> mt.trapezoid([1,2,3], dx=2).execute()
8.0
>>> a = mt.arange(6).reshape(2, 3)
>>> a.execute()
array([[0, 1, 2],
       [3, 4, 5]])
>>> mt.trapezoid(a, axis=0).execute()
array([1.5, 2.5, 3.5])
>>> mt.trapezoid(a, axis=1).execute()
array([2.,  8.])
```
