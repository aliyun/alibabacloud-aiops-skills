# maxframe.tensor.isclose

### maxframe.tensor.isclose(a, b, rtol=1e-05, atol=1e-08, equal_nan=False)

Returns a boolean tensor where two tensors are element-wise equal within a
tolerance.

The tolerance values are positive, typically very small numbers.  The
relative difference (rtol \* abs(b)) and the absolute difference
atol are added together to compare against the absolute difference
between a and b.

* **Parameters:**
  * **a** (*array_like*) – Input tensors to compare.
  * **b** (*array_like*) – Input tensors to compare.
  * **rtol** ([*float*](https://docs.python.org/3/library/functions.html#float)) – The relative tolerance parameter (see Notes).
  * **atol** ([*float*](https://docs.python.org/3/library/functions.html#float)) – The absolute tolerance parameter (see Notes).
  * **equal_nan** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Whether to compare NaN’s as equal.  If True, NaN’s in a will be
    considered equal to NaN’s in b in the output tensor.
* **Returns:**
  **y** – Returns a boolean tensor of where a and b are equal within the
  given tolerance. If both a and b are scalars, returns a single
  boolean value.
* **Return type:**
  array_like

#### SEE ALSO
[`allclose`](maxframe.tensor.allclose.md#maxframe.tensor.allclose)

### Notes

For finite values, isclose uses the following equation to test whether
two floating point values are equivalent.

> absolute(a - b) <= (atol + rtol \* absolute(b))

The above equation is not symmetric in a and b, so that
isclose(a, b) might be different from isclose(b, a) in
some rare cases.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.isclose([1e10,1e-7], [1.00001e10,1e-8]).execute()
array([True, False])
>>> mt.isclose([1e10,1e-8], [1.00001e10,1e-9]).execute()
array([True, True])
>>> mt.isclose([1e10,1e-8], [1.0001e10,1e-9]).execute()
array([False, True])
>>> mt.isclose([1.0, mt.nan], [1.0, mt.nan]).execute()
array([True, False])
>>> mt.isclose([1.0, mt.nan], [1.0, mt.nan], equal_nan=True).execute()
array([True, True])
```
