# maxframe.tensor.allclose

### maxframe.tensor.allclose(a, b, rtol=1e-05, atol=1e-08, equal_nan=False)

Returns True if two tensors are element-wise equal within a tolerance.

The tolerance values are positive, typically very small numbers.  The
relative difference (rtol \* abs(b)) and the absolute difference
atol are added together to compare against the absolute difference
between a and b.

If either array contains one or more NaNs, False is returned.
Infs are treated as equal if they are in the same place and of the same
sign in both tensors.

* **Parameters:**
  * **a** (*array_like*) – Input tensors to compare.
  * **b** (*array_like*) – Input tensors to compare.
  * **rtol** ([*float*](https://docs.python.org/3/library/functions.html#float)) – The relative tolerance parameter (see Notes).
  * **atol** ([*float*](https://docs.python.org/3/library/functions.html#float)) – The absolute tolerance parameter (see Notes).
  * **equal_nan** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Whether to compare NaN’s as equal.  If True, NaN’s in a will be
    considered equal to NaN’s in b in the output tensor.
* **Returns:**
  **allclose** – Returns True if the two tensors are equal within the given
  tolerance; False otherwise.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`isclose`](maxframe.tensor.isclose.md#maxframe.tensor.isclose), [`all`](maxframe.tensor.all.md#maxframe.tensor.all), [`any`](maxframe.tensor.any.md#maxframe.tensor.any), [`equal`](maxframe.tensor.equal.md#maxframe.tensor.equal)

### Notes

If the following equation is element-wise True, then allclose returns
True.

> absolute(a - b) <= (atol + rtol \* absolute(b))

The above equation is not symmetric in a and b, so that
`allclose(a, b)` might be different from `allclose(b, a)` in
some rare cases.

The comparison of a and b uses standard broadcasting, which
means that a and b need not have the same shape in order for
`allclose(a, b)` to evaluate to True.  The same is true for
equal but not array_equal.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.allclose([1e10,1e-7], [1.00001e10,1e-8]).execute()
False
>>> mt.allclose([1e10,1e-8], [1.00001e10,1e-9]).execute()
True
>>> mt.allclose([1e10,1e-8], [1.0001e10,1e-9]).execute()
False
>>> mt.allclose([1.0, mt.nan], [1.0, mt.nan]).execute()
False
>>> mt.allclose([1.0, mt.nan], [1.0, mt.nan], equal_nan=True).execute()
True
```
