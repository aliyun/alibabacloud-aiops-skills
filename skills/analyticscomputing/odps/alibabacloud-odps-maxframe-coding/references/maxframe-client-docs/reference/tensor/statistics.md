# Statistics

## Order statistics

| [`maxframe.tensor.ptp`](generated/maxframe.tensor.ptp.md#maxframe.tensor.ptp)                      | Range of values (maximum - minimum) along an axis.                          |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`maxframe.tensor.percentile`](generated/maxframe.tensor.percentile.md#maxframe.tensor.percentile) | Compute the q-th percentile of the data along the specified axis.           |
| [`maxframe.tensor.quantile`](generated/maxframe.tensor.quantile.md#maxframe.tensor.quantile)       | Compute the q-th quantile of the data along the specified axis.             |
| [`maxframe.tensor.nanmin`](generated/maxframe.tensor.nanmin.md#maxframe.tensor.nanmin)             | Return minimum of a tensor or minimum along an axis, ignoring any NaNs.     |
| [`maxframe.tensor.nanmax`](generated/maxframe.tensor.nanmax.md#maxframe.tensor.nanmax)             | Return the maximum of an array or maximum along an axis, ignoring any NaNs. |

## Average and variances

| [`maxframe.tensor.median`](generated/maxframe.tensor.median.md#maxframe.tensor.median)    | Compute the median along the specified axis.                                  |
|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`maxframe.tensor.average`](generated/maxframe.tensor.average.md#maxframe.tensor.average) | Compute the weighted average along the specified axis.                        |
| [`maxframe.tensor.mean`](generated/maxframe.tensor.mean.md#maxframe.tensor.mean)          | Compute the arithmetic mean along the specified axis.                         |
| [`maxframe.tensor.std`](generated/maxframe.tensor.std.md#maxframe.tensor.std)             | Compute the standard deviation along the specified axis.                      |
| [`maxframe.tensor.var`](generated/maxframe.tensor.var.md#maxframe.tensor.var)             | Compute the variance along the specified axis.                                |
| [`maxframe.tensor.nanmean`](generated/maxframe.tensor.nanmean.md#maxframe.tensor.nanmean) | Compute the arithmetic mean along the specified axis, ignoring NaNs.          |
| [`maxframe.tensor.nanstd`](generated/maxframe.tensor.nanstd.md#maxframe.tensor.nanstd)    | Compute the standard deviation along the specified axis, while ignoring NaNs. |
| [`maxframe.tensor.nanvar`](generated/maxframe.tensor.nanvar.md#maxframe.tensor.nanvar)    | Compute the variance along the specified axis, while ignoring NaNs.           |

## Correlating

| [`maxframe.tensor.corrcoef`](generated/maxframe.tensor.corrcoef.md#maxframe.tensor.corrcoef)   | Return Pearson product-moment correlation coefficients.   |
|------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| [`maxframe.tensor.cov`](generated/maxframe.tensor.cov.md#maxframe.tensor.cov)                  | Estimate a covariance matrix, given data and weights.     |

## Histograms

| [`maxframe.tensor.histogram`](generated/maxframe.tensor.histogram.md#maxframe.tensor.histogram)                               | Compute the histogram of a set of data.                                          |
|-------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`maxframe.tensor.bincount`](generated/maxframe.tensor.bincount.md#maxframe.tensor.bincount)                                  | Count number of occurrences of each value in array of non-negative ints.         |
| [`maxframe.tensor.histogram_bin_edges`](generated/maxframe.tensor.histogram_bin_edges.md#maxframe.tensor.histogram_bin_edges) | Function to calculate only the edges of the bins used by the histogram function. |
| [`maxframe.tensor.digitize`](generated/maxframe.tensor.digitize.md#maxframe.tensor.digitize)                                  | Return the indices of the bins to which each value in input tensor belongs.      |
