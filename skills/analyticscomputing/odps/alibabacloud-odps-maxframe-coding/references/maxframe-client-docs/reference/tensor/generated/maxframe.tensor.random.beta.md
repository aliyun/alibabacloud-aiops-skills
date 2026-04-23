# maxframe.tensor.random.beta

### maxframe.tensor.random.beta(a, b, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Beta distribution.

The Beta distribution is a special case of the Dirichlet distribution,
and is related to the Gamma distribution.  It has the probability
distribution function

$$
f(x; a,b) = \frac{1}{B(\alpha, \beta)} x^{\alpha - 1}
(1 - x)^{\beta - 1},

$$

where the normalisation, B, is the beta function,

$$
B(\alpha, \beta) = \int_0^1 t^{\alpha - 1}
(1 - t)^{\beta - 1} dt.

$$

It is often seen in Bayesian inference and order statistics.

* **Parameters:**
  * **a** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Alpha, non-negative.
  * **b** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Beta, non-negative.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `a` and `b` are both scalars.
    Otherwise, `mt.broadcast(a, b).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized beta distribution.
* **Return type:**
  Tensor or scalar
