# maxframe.tensor.random.rayleigh

### maxframe.tensor.random.rayleigh(scale=1.0, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a Rayleigh distribution.

The $\chi$ and Weibull distributions are generalizations of the
Rayleigh.

* **Parameters:**
  * **scale** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats* *,* *optional*) – Scale, also equals the mode. Should be >= 0. Default is 1.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `scale` is a scalar.  Otherwise,
    `mt.array(scale).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized Rayleigh distribution.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the Rayleigh distribution is

$$
P(x;scale) = \frac{x}{scale^2}e^{\frac{-x^2}{2 \cdotp scale^2}}

$$

The Rayleigh distribution would arise, for example, if the East
and North components of the wind velocity had identical zero-mean
Gaussian distributions.  Then the wind speed would have a Rayleigh
distribution.

### References

* <a id='id1'>**[1]**</a> Brighton Webs Ltd., “Rayleigh Distribution,” [http://www.brighton-webs.co.uk/distributions/rayleigh.asp](http://www.brighton-webs.co.uk/distributions/rayleigh.asp)
* <a id='id2'>**[2]**</a> Wikipedia, “Rayleigh distribution” [http://en.wikipedia.org/wiki/Rayleigh_distribution](http://en.wikipedia.org/wiki/Rayleigh_distribution)

### Examples

Draw values from the distribution and plot the histogram

```pycon
>>> import matplotlib.pyplot as plt
>>> import maxframe.tensor as mt
```

```pycon
>>> values = plt.hist(mt.random.rayleigh(3, 100000).execute(), bins=200, normed=True)
```

Wave heights tend to follow a Rayleigh distribution. If the mean wave
height is 1 meter, what fraction of waves are likely to be larger than 3
meters?

```pycon
>>> meanvalue = 1
>>> modevalue = mt.sqrt(2 / mt.pi) * meanvalue
>>> s = mt.random.rayleigh(modevalue, 1000000)
```

The percentage of waves larger than 3 meters is:

```pycon
>>> (100.*mt.sum(s>3)/1000000.).execute()
0.087300000000000003
```
