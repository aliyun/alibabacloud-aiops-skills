# maxframe.tensor.random.exponential

### maxframe.tensor.random.exponential(scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from an exponential distribution.

Its probability density function is

$$
f(x; \frac{1}{\beta}) = \frac{1}{\beta} \exp(-\frac{x}{\beta}),

$$

for `x > 0` and 0 elsewhere. $\beta$ is the scale parameter,
which is the inverse of the rate parameter $\lambda = 1/\beta$.
The rate parameter is an alternative, widely used parameterization
of the exponential distribution <sup>[3](#id6)</sup>.

The exponential distribution is a continuous analogue of the
geometric distribution.  It describes many common situations, such as
the size of raindrops measured over many rainstorms <sup>[1](#id4)</sup>, or the time
between page requests to Wikipedia <sup>[2](#id5)</sup>.

* **Parameters:**
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – The scale parameter, $\beta = 1/\lambda$.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `scale` is a scalar.  Otherwise,
    `np.array(scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized exponential distribution.
* **Return type:**
  Tensor or scalar

### References

* <a id='id4'>**[1]**</a> Peyton Z. Peebles Jr., “Probability, Random Variables and Random Signal Principles”, 4th ed, 2001, p. 57.
* <a id='id5'>**[2]**</a> Wikipedia, “Poisson process”, [http://en.wikipedia.org/wiki/Poisson_process](http://en.wikipedia.org/wiki/Poisson_process)
* <a id='id6'>**[3]**</a> Wikipedia, “Exponential distribution”, [http://en.wikipedia.org/wiki/Exponential_distribution](http://en.wikipedia.org/wiki/Exponential_distribution)
