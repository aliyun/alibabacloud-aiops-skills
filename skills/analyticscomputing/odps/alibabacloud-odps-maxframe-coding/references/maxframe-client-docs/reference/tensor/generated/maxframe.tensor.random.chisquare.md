# maxframe.tensor.random.chisquare

### maxframe.tensor.random.chisquare(df, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a chi-square distribution.

When df independent random variables, each with standard normal
distributions (mean 0, variance 1), are squared and summed, the
resulting distribution is chi-square (see Notes).  This distribution
is often used in hypothesis testing.

* **Parameters:**
  * **df** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Number of degrees of freedom, should be > 0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `df` is a scalar.  Otherwise,
    `mt.array(df).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized chi-square distribution.
* **Return type:**
  Tensor or scalar
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – When df <= 0 or when an inappropriate size (e.g. `size=-1`)
      is given.

### Notes

The variable obtained by summing the squares of df independent,
standard normally distributed random variables:

$$
Q = \sum_{i=0}^{\mathtt{df}} X^2_i

$$

is chi-square distributed, denoted

$$
Q \sim \chi^2_k.

$$

The probability density function of the chi-squared distribution is

$$
p(x) = \frac{(1/2)^{k/2}}{\Gamma(k/2)}
x^{k/2 - 1} e^{-x/2},

$$

where $\Gamma$ is the gamma function,

$$
\Gamma(x) = \int_0^{-\infty} t^{x - 1} e^{-t} dt.

$$

### References

* <a id='id1'>**[1]**</a> NIST “Engineering Statistics Handbook” [http://www.itl.nist.gov/div898/handbook/eda/section3/eda3666.htm](http://www.itl.nist.gov/div898/handbook/eda/section3/eda3666.htm)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.chisquare(2,4).execute()
array([ 1.89920014,  9.00867716,  3.13710533,  5.62318272])
```
