# maxframe.tensor.random.triangular

### maxframe.tensor.random.triangular(left, mode, right, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the triangular distribution over the
interval `[left, right]`.

The triangular distribution is a continuous probability
distribution with lower limit left, peak at mode, and upper
limit right. Unlike the other distributions, these parameters
directly define the shape of the pdf.

* **Parameters:**
  * **left** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Lower limit.
  * **mode** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – The value where the peak of the distribution occurs.
    The value should fulfill the condition `left <= mode <= right`.
  * **right** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Upper limit, should be larger than left.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `left`, `mode`, and `right`
    are all scalars.  Otherwise, `mt.broadcast(left, mode, right).size`
    samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized triangular distribution.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the triangular distribution is

$$
P(x;l, m, r) = \begin{cases}
\frac{2(x-l)}{(r-l)(m-l)}& \text{for $l \leq x \leq m$},\\
\frac{2(r-x)}{(r-l)(r-m)}& \text{for $m \leq x \leq r$},\\
0& \text{otherwise}.
\end{cases}

$$

The triangular distribution is often used in ill-defined
problems where the underlying distribution is not known, but
some knowledge of the limits and mode exists. Often it is used
in simulations.

### References

* <a id='id1'>**[1]**</a> Wikipedia, “Triangular distribution” [http://en.wikipedia.org/wiki/Triangular_distribution](http://en.wikipedia.org/wiki/Triangular_distribution)

### Examples

Draw values from the distribution and plot the histogram:

```pycon
>>> import matplotlib.pyplot as plt
>>> import maxframe.tensor as mt
>>> h = plt.hist(mt.random.triangular(-3, 0, 8, 100000).execute(), bins=200,
...              normed=True)
>>> plt.show()
```
