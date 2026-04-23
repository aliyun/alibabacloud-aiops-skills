# maxframe.tensor.histogram

### maxframe.tensor.histogram(a, bins=10, range=None, weights=None, density=None)

Compute the histogram of a set of data.

* **Parameters:**
  * **a** (*array_like*) – Input data. The histogram is computed over the flattened tensor.
  * **bins** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *scalars* *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – 

    If bins is an int, it defines the number of equal-width
    bins in the given range (10, by default). If bins is a
    sequence, it defines a monotonically increasing tensor of bin edges,
    including the rightmost edge, allowing for non-uniform bin widths.

    If bins is a string, it defines the method used to calculate the
    optimal bin width, as defined by histogram_bin_edges.
  * **range** ( *(*[*float*](https://docs.python.org/3/library/functions.html#float) *,* [*float*](https://docs.python.org/3/library/functions.html#float) *)* *,* *optional*) – The lower and upper range of the bins.  If not provided, range
    is simply `(a.min(), a.max())`.  Values outside the range are
    ignored. The first element of the range must be less than or
    equal to the second. range affects the automatic bin
    computation as well. While bin width is computed to be optimal
    based on the actual data within range, the bin count will fill
    the entire range including portions containing no data.
  * **weights** (*array_like* *,* *optional*) – A tensor of weights, of the same shape as a.  Each value in
    a only contributes its associated weight towards the bin count
    (instead of 1). If density is True, the weights are
    normalized, so that the integral of the density over the range
    remains 1.
  * **density** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – 

    If `False`, the result will contain the number of samples in
    each bin. If `True`, the result is the value of the
    probability *density* function at the bin, normalized such that
    the *integral* over the range is 1. Note that the sum of the
    histogram values will not be equal to 1 unless bins of unity
    width are chosen; it is not a probability *mass* function.

    Overrides the `normed` keyword if given.
* **Returns:**
  * **hist** (*tensor*) – The values of the histogram. See density and weights for a
    description of the possible semantics.
  * **bin_edges** (*tensor of dtype float*) – Return the bin edges `(length(hist)+1)`.

#### SEE ALSO
`histogramdd`, [`bincount`](maxframe.tensor.bincount.md#maxframe.tensor.bincount), `searchsorted`, [`digitize`](maxframe.tensor.digitize.md#maxframe.tensor.digitize), [`histogram_bin_edges`](maxframe.tensor.histogram_bin_edges.md#maxframe.tensor.histogram_bin_edges)

### Notes

All but the last (righthand-most) bin is half-open.  In other words,
if bins is:

```default
[1, 2, 3, 4]
```

then the first bin is `[1, 2)` (including 1, but excluding 2) and
the second `[2, 3)`.  The last bin, however, is `[3, 4]`, which
*includes* 4.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.histogram([1, 2, 1], bins=[0, 1, 2, 3]).execute()
(array([0, 2, 1]), array([0, 1, 2, 3]))
>>> mt.histogram(mt.arange(4), bins=mt.arange(5), density=True).execute()
(array([0.25, 0.25, 0.25, 0.25]), array([0, 1, 2, 3, 4]))
>>> mt.histogram([[1, 2, 1], [1, 0, 1]], bins=[0,1,2,3]).execute()
(array([1, 4, 1]), array([0, 1, 2, 3]))
```

```pycon
>>> a = mt.arange(5)
>>> hist, bin_edges = mt.histogram(a, density=True)
>>> hist.execute()
array([0.5, 0. , 0.5, 0. , 0. , 0.5, 0. , 0.5, 0. , 0.5])
>>> hist.sum().execute()
2.4999999999999996
>>> mt.sum(hist * mt.diff(bin_edges)).execute()
1.0
```

Automated Bin Selection Methods example, using 2 peak random data
with 2000 points:

```pycon
>>> import matplotlib.pyplot as plt
>>> rng = mt.random.RandomState(10)  # deterministic random data
>>> a = mt.hstack((rng.normal(size=1000),
...                rng.normal(loc=5, scale=2, size=1000)))
>>> _ = plt.hist(np.asarray(a), bins='auto')  # arguments are passed to np.histogram
>>> plt.title("Histogram with 'auto' bins")
Text(0.5, 1.0, "Histogram with 'auto' bins")
>>> plt.show()
```
