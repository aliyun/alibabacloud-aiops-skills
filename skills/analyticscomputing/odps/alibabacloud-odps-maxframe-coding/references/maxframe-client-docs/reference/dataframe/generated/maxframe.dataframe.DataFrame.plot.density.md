# maxframe.dataframe.DataFrame.plot.density

#### DataFrame.plot.density(\*args, \*\*kwargs)

Generate Kernel Density Estimate plot using Gaussian kernels.

In statistics, [kernel density estimation](https://en.wikipedia.org/wiki/Kernel_density_estimation) (KDE) is a non-parametric
way to estimate the probability density function (PDF) of a random
variable. This function uses Gaussian kernels and includes automatic
bandwidth determination.

* **Parameters:**
  * **bw_method** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *scalar* *or* *callable* *,* *optional*) – The method used to calculate the estimator bandwidth. This can be
    ‘scott’, ‘silverman’, a scalar constant or a callable.
    If None (default), ‘scott’ is used.
    See [`scipy.stats.gaussian_kde`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html#scipy.stats.gaussian_kde) for more information.
  * **ind** (*NumPy array* *or* [*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Evaluation points for the estimated PDF. If None (default),
    1000 equally spaced points are used. If ind is a NumPy array, the
    KDE is evaluated at the points passed. If ind is an integer,
    ind number of equally spaced points are used.
  * **\*\*kwargs** – Additional keyword arguments are documented in
    [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Return type:**
  [matplotlib.axes.Axes](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html#matplotlib.axes.Axes) or [numpy.ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray) of them

#### SEE ALSO
[`scipy.stats.gaussian_kde`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html#scipy.stats.gaussian_kde)
: Representation of a kernel-density estimate using Gaussian kernels. This is the function used internally to estimate the PDF.

### Examples

Given a Series of points randomly sampled from an unknown
distribution, estimate its PDF using KDE with automatic
bandwidth determination and plot the results, evaluating them at
1000 equally spaced points (default):

A scalar bandwidth can be specified. Using a small bandwidth value can
lead to over-fitting, while using a large bandwidth value may result
in under-fitting:

Finally, the ind parameter determines the evaluation points for the
plot of the estimated PDF:

For DataFrame, it works in the same way:

A scalar bandwidth can be specified. Using a small bandwidth value can
lead to over-fitting, while using a large bandwidth value may result
in under-fitting:

Finally, the ind parameter determines the evaluation points for the
plot of the estimated PDF:
