# maxframe.tensor.digitize

### maxframe.tensor.digitize(x, bins, right=False)

Return the indices of the bins to which each value in input tensor belongs.

Each index `i` returned is such that `bins[i-1] <= x < bins[i]` if
bins is monotonically increasing, or `bins[i-1] > x >= bins[i]` if
bins is monotonically decreasing. If values in x are beyond the
bounds of bins, 0 or `len(bins)` is returned as appropriate. If right
is True, then the right bin is closed so that the index `i` is such
that `bins[i-1] < x <= bins[i]` or `bins[i-1] >= x > bins[i]` if bins
is monotonically increasing or decreasing, respectively.

* **Parameters:**
  * **x** (*array_like*) – Input tensor to be binned.
  * **bins** (*array_like*) – Array of bins. It has to be 1-dimensional and monotonic.
  * **right** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Indicating whether the intervals include the right or the left bin
    edge. Default behavior is (right==False) indicating that the interval
    does not include the right edge. The left bin end is open in this
    case, i.e., bins[i-1] <= x < bins[i] is the default behavior for
    monotonically increasing bins.
* **Returns:**
  **out** – Output tensor of indices, of same shape as x.
* **Return type:**
  Tensor of ints
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If bins is not monotonic.
  * [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If the type of the input is complex.

#### SEE ALSO
[`bincount`](maxframe.tensor.bincount.md#maxframe.tensor.bincount), [`histogram`](maxframe.tensor.histogram.md#maxframe.tensor.histogram), [`unique`](maxframe.tensor.unique.md#maxframe.tensor.unique), `searchsorted`

### Notes

If values in x are such that they fall outside the bin range,
attempting to index bins with the indices that digitize returns
will result in an IndexError.

mt.digitize is  implemented in terms of mt.searchsorted. This means
that a binary search is used to bin the values, which scales much better
for larger number of bins than the previous linear search. It also removes
the requirement for the input array to be 1-dimensional.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([0.2, 6.4, 3.0, 1.6])
>>> bins = mt.array([0.0, 1.0, 2.5, 4.0, 10.0])
>>> inds = mt.digitize(x, bins)
>>> inds.execute()
array([1, 4, 3, 2])
```

```pycon
>>> x = mt.array([1.2, 10.0, 12.4, 15.5, 20.])
>>> bins = mt.array([0, 5, 10, 15, 20])
>>> mt.digitize(x,bins,right=True).execute()
array([1, 2, 3, 4, 4])
>>> mt.digitize(x,bins,right=False).execute()
array([1, 3, 3, 4, 5])
```
