# maxframe.tensor.random.wald

### maxframe.tensor.random.wald(mean, scale, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Wald, or inverse Gaussian, distribution.

As the scale approaches infinity, the distribution becomes more like a
Gaussian. Some references claim that the Wald is an inverse Gaussian
with mean equal to 1, but this is by no means universal.

The inverse Gaussian distribution was first studied in relationship to
Brownian motion. In 1956 M.C.K. Tweedie used the name inverse Gaussian
because there is an inverse relationship between the time to cover a
unit distance and distance covered in unit time.

* **Parameters:**
  * **mean** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Distribution mean, should be > 0.
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Scale parameter, should be >= 0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `mean` and `scale` are both scalars.
    Otherwise, `np.broadcast(mean, scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Wald distribution.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the Wald distribution is

$$
P(x;mean,scale) = \sqrt{\frac{scale}{2\pi x^3}}e^
\frac{-scale(x-mean)^2}{2\cdotp mean^2x}

$$

As noted above the inverse Gaussian distribution first arise
from attempts to model Brownian motion. It is also a
competitor to the Weibull for use in reliability modeling and
modeling stock returns and interest rate processes.

### References

* <a id='id1'>**[1]**</a> Brighton Webs Ltd., Wald Distribution, [http://www.brighton-webs.co.uk/distributions/wald.asp](http://www.brighton-webs.co.uk/distributions/wald.asp)
* <a id='id2'>**[2]**</a> Chhikara, Raj S., and Folks, J. Leroy, “The Inverse Gaussian Distribution: Theory : Methodology, and Applications”, CRC Press, 1988.
* <a id='id3'>**[3]**</a> Wikipedia, “Wald distribution” [http://en.wikipedia.org/wiki/Wald_distribution](http://en.wikipedia.org/wiki/Wald_distribution)

### Examples

Draw values from the distribution and plot the histogram:

```pycon
>>> import matplotlib.pyplot as plt
>>> import maxframe.tensor as mt
>>> h = plt.hist(mt.random.wald(3, 2, 100000).execute(), bins=200, normed=True)
>>> plt.show()
```
