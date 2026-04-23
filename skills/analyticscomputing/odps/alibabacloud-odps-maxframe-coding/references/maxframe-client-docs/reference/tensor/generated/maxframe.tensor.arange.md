# maxframe.tensor.arange

### maxframe.tensor.arange(\*args, \*\*kwargs)

Return evenly spaced values within a given interval.

Values are generated within the half-open interval `[start, stop)`
(in other words, the interval including start but excluding stop).
For integer arguments the function is equivalent to the Python built-in
[range](http://docs.python.org/lib/built-in-funcs.html) function,
but returns a tensor rather than a list.

When using a non-integer step, such as 0.1, the results will often not
be consistent.  It is better to use `linspace` for these cases.

* **Parameters:**
  * **start** (*number* *,* *optional*) – Start of interval.  The interval includes this value.  The default
    start value is 0.
  * **stop** (*number*) – End of interval.  The interval does not include this value, except
    in some cases where step is not an integer and floating point
    round-off affects the length of out.
  * **step** (*number* *,* *optional*) – Spacing between values.  For any output out, this is the distance
    between two adjacent values, `out[i+1] - out[i]`.  The default
    step size is 1.  If step is specified as a position argument,
    start must also be given.
  * **dtype** (*dtype*) – The type of the output tensor.  If dtype is not given, infer the data
    type from the other input arguments.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
* **Returns:**
  **arange** – Tensor of evenly spaced values.

  For floating point arguments, the length of the result is
  `ceil((stop - start)/step)`.  Because of floating point overflow,
  this rule may result in the last element of out being greater
  than stop.
* **Return type:**
  Tensor

#### SEE ALSO
[`linspace`](maxframe.tensor.linspace.md#maxframe.tensor.linspace)
: Evenly spaced numbers with careful handling of endpoints.

[`ogrid`](maxframe.tensor.ogrid.md#maxframe.tensor.ogrid)
: Tensors of evenly spaced numbers in N-dimensions.

[`mgrid`](maxframe.tensor.mgrid.md#maxframe.tensor.mgrid)
: Grid-shaped tensors of evenly spaced numbers in N-dimensions.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.arange(3).execute()
array([0, 1, 2])
>>> mt.arange(3.0).execute()
array([ 0.,  1.,  2.])
>>> mt.arange(3,7).execute()
array([3, 4, 5, 6])
>>> mt.arange(3,7,2).execute()
array([3, 5])
```
