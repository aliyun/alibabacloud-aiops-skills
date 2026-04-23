# maxframe.tensor.histogram_bin_edges

### maxframe.tensor.histogram_bin_edges(a, bins=10, range=None, weights=None)

Function to calculate only the edges of the bins used by the histogram
function.

* **Parameters:**
  * **a** (*array_like*) – Input data. The histogram is computed over the flattened tensor.
  * **bins** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *scalars* *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – 

    If bins is an int, it defines the number of equal-width
    bins in the given range (10, by default). If bins is a
    sequence, it defines the bin edges, including the rightmost
    edge, allowing for non-uniform bin widths.

    If bins is a string from the list below, histogram_bin_edges will use
    the method chosen to calculate the optimal bin width and
    consequently the number of bins (see Notes for more detail on
    the estimators) from the data that falls within the requested
    range. While the bin width will be optimal for the actual data
    in the range, the number of bins will be computed to fill the
    entire range, including the empty portions. For visualisation,
    using the ‘auto’ option is suggested. Weighted data is not
    supported for automated bin size selection.

    ’auto’
    : Maximum of the ‘sturges’ and ‘fd’ estimators. Provides good
      all around performance.

    ’fd’ (Freedman Diaconis Estimator)
    : Robust (resilient to outliers) estimator that takes into
      account data variability and data size.

    ’doane’
    : An improved version of Sturges’ estimator that works better
      with non-normal datasets.

    ’scott’
    : Less robust estimator that that takes into account data
      variability and data size.

    ’stone’
    : Estimator based on leave-one-out cross-validation estimate of
      the integrated squared error. Can be regarded as a generalization
      of Scott’s rule.

    ’rice’
    : Estimator does not take variability into account, only data
      size. Commonly overestimates number of bins required.

    ’sturges’
    : R’s default method, only accounts for data size. Only
      optimal for gaussian data and underestimates number of bins
      for large non-gaussian datasets.

    ’sqrt’
    : Square root (of data size) estimator, used by Excel and
      other programs for its speed and simplicity.
  * **range** ( *(*[*float*](https://docs.python.org/3/library/functions.html#float) *,* [*float*](https://docs.python.org/3/library/functions.html#float) *)* *,* *optional*) – The lower and upper range of the bins.  If not provided, range
    is simply `(a.min(), a.max())`.  Values outside the range are
    ignored. The first element of the range must be less than or
    equal to the second. range affects the automatic bin
    computation as well. While bin width is computed to be optimal
    based on the actual data within range, the bin count will fill
    the entire range including portions containing no data.
  * **weights** (*array_like* *,* *optional*) – A tensor of weights, of the same shape as a.  Each value in
    a only contributes its associated weight towards the bin count
    (instead of 1). This is currently not used by any of the bin estimators,
    but may be in the future.
* **Returns:**
  **bin_edges** – The edges to pass into histogram
* **Return type:**
  tensor of dtype float

#### SEE ALSO
[`histogram`](maxframe.tensor.histogram.md#maxframe.tensor.histogram)

### Notes

The methods to estimate the optimal number of bins are well founded
in literature, and are inspired by the choices R provides for
histogram visualisation. Note that having the number of bins
proportional to $n^{1/3}$ is asymptotically optimal, which is
why it appears in most estimators. These are simply plug-in methods
that give good starting points for number of bins. In the equations
below, $h$ is the binwidth and $n_h$ is the number of
bins. All estimators that compute bin counts are recast to bin width
using the ptp of the data. The final bin count is obtained from
`np.round(np.ceil(range / h))`.

‘auto’ (maximum of the ‘sturges’ and ‘fd’ estimators)
: A compromise to get a good value. For small datasets the Sturges
  value will usually be chosen, while larger datasets will usually
  default to FD.  Avoids the overly conservative behaviour of FD
  and Sturges for small and large datasets respectively.
  Switchover point is usually $a.size \approx 1000$.

‘fd’ (Freedman Diaconis Estimator)
: $$
  h = 2 \frac{IQR}{n^{1/3}}
  <br/>
  $$
  <br/>
  The binwidth is proportional to the interquartile range (IQR)
  and inversely proportional to cube root of a.size. Can be too
  conservative for small datasets, but is quite good for large
  datasets. The IQR is very robust to outliers.

‘scott’
: $$
  h = \sigma \sqrt[3]{\frac{24 * \sqrt{\pi}}{n}}
  <br/>
  $$
  <br/>
  The binwidth is proportional to the standard deviation of the
  data and inversely proportional to cube root of `x.size`. Can
  be too conservative for small datasets, but is quite good for
  large datasets. The standard deviation is not very robust to
  outliers. Values are very similar to the Freedman-Diaconis
  estimator in the absence of outliers.

‘rice’
: $$
  n_h = 2n^{1/3}
  <br/>
  $$
  <br/>
  The number of bins is only proportional to cube root of
  `a.size`. It tends to overestimate the number of bins and it
  does not take into account data variability.

‘sturges’
: $$
  n_h = \log _{2}n+1
  <br/>
  $$
  <br/>
  The number of bins is the base 2 log of `a.size`.  This
  estimator assumes normality of data and is too conservative for
  larger, non-normal datasets. This is the default method in R’s
  `hist` method.

‘doane’
: $$
  n_h = 1 + \log_{2}(n) +
              \log_{2}(1 + \frac{|g_1|}{\sigma_{g_1}})
  <br/>
  g_1 = mean[(\frac{x - \mu}{\sigma})^3]
  <br/>
  \sigma_{g_1} = \sqrt{\frac{6(n - 2)}{(n + 1)(n + 3)}}
  $$
  <br/>
  An improved version of Sturges’ formula that produces better
  estimates for non-normal datasets. This estimator attempts to
  account for the skew of the data.

‘sqrt’
: $$
  n_h = \sqrt n
  <br/>
  $$
  <br/>
  The simplest and fastest estimator. Only takes into account the
  data size.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> arr = mt.array([0, 0, 0, 1, 2, 3, 3, 4, 5])
>>> mt.histogram_bin_edges(arr, bins='auto', range=(0, 1)).execute()
array([0.  , 0.25, 0.5 , 0.75, 1.  ])
>>> mt.histogram_bin_edges(arr, bins=2).execute()
array([0. , 2.5, 5. ])
```

For consistency with histogram, a tensor of pre-computed bins is
passed through unmodified:

```pycon
>>> mt.histogram_bin_edges(arr, [1, 2]).execute()
array([1, 2])
```

This function allows one set of bins to be computed, and reused across
multiple histograms:

```pycon
>>> shared_bins = mt.histogram_bin_edges(arr, bins='auto')
>>> shared_bins.execute()
array([0., 1., 2., 3., 4., 5.])
```

```pycon
>>> group_id = mt.array([0, 1, 1, 0, 1, 1, 0, 1, 1])
>>> a = arr[group_id == 0]
>>> a.execute()
array([0, 1, 3])
>>> hist_0, _ = mt.histogram(a, bins=shared_bins).execute()
>>> b = arr[group_id == 1]
>>> b.execute()
array([0, 0, 2, 3, 4, 5])
>>> hist_1, _ = mt.histogram(b, bins=shared_bins).execute()
```

```pycon
>>> hist_0; hist_1
array([1, 1, 0, 1, 0])
array([2, 0, 1, 1, 2])
```

Which gives more easily comparable results than using separate bins for
each histogram:

```pycon
>>> hist_0, bins_0 = mt.histogram(a, bins='auto').execute()
>>> hist_1, bins_1 = mt.histogram(b, bins='auto').execute()
>>> hist_0; hist_1
array([1, 1, 1])
array([2, 1, 1, 2])
>>> bins_0; bins_1
array([0., 1., 2., 3.])
array([0.  , 1.25, 2.5 , 3.75, 5.  ])
```
