# maxframe.tensor.in1d

### maxframe.tensor.in1d(ar1: TileableType | [ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray), ar2: TileableType | [ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray) | [list](https://docs.python.org/3/library/stdtypes.html#list), assume_unique: [bool](https://docs.python.org/3/library/functions.html#bool) = False, invert: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Test whether each element of a 1-D tensor is also present in a second tensor.

Returns a boolean tensor the same length as ar1 that is True
where an element of ar1 is in ar2 and False otherwise.

We recommend using [`isin()`](maxframe.tensor.isin.md#maxframe.tensor.isin) instead of in1d for new code.

* **Parameters:**
  * **ar1** ( *(**M* *,* *)* *Tensor*) – Input tensor.
  * **ar2** (*array_like*) – The values against which to test each value of ar1.
  * **assume_unique** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, the input tensors are both assumed to be unique, which
    can speed up the calculation.  Default is False.
  * **invert** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, the values in the returned tensor are inverted (that is,
    False where an element of ar1 is in ar2 and True otherwise).
    Default is False. `np.in1d(a, b, invert=True)` is equivalent
    to (but is faster than) `np.invert(in1d(a, b))`.
* **Returns:**
  **in1d** – The values ar1[in1d] are in ar2.
* **Return type:**
  (M,) Tensor, [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`isin`](maxframe.tensor.isin.md#maxframe.tensor.isin)
: Version of this function that preserves the shape of ar1.

`numpy.lib.arraysetops`
: Module with a number of other functions for performing set operations on arrays.

### Notes

in1d can be considered as an element-wise function version of the
python keyword in, for 1-D sequences. `in1d(a, b)` is roughly
equivalent to `mt.array([item in b for item in a])`.
However, this idea fails if ar2 is a set, or similar (non-sequence)
container:  As `ar2` is converted to a tensor, in those cases
`asarray(ar2)` is an object tensor rather than the expected tensor of
contained values.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> test = mt.array([0, 1, 2, 5, 0])
>>> states = [0, 2]
>>> mask = mt.in1d(test, states)
>>> mask.execute()
array([ True, False,  True, False,  True])
>>> test[mask].execute()
array([0, 2, 0])
>>> mask = mt.in1d(test, states, invert=True)
>>> mask.execute()
array([False,  True, False,  True, False])
>>> test[mask].execute()
array([1, 5])
```
