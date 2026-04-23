# maxframe.tensor.random.standard_t

### maxframe.tensor.random.standard_t(df, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from a standard Student’s t distribution with df degrees
of freedom.

A special case of the hyperbolic distribution.  As df gets
large, the result resembles that of the standard normal
distribution (standard_normal).

* **Parameters:**
  * **df** ([*float*](https://docs.python.org/3/library/functions.html#float) *or* *array_like* *of* *floats*) – Degrees of freedom, should be > 0.
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  If size is `None` (default),
    a single value is returned if `df` is a scalar.  Otherwise,
    `mt.array(df).size` samples are drawn.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **out** – Drawn samples from the parameterized standard Student’s t distribution.
* **Return type:**
  Tensor or scalar

### Notes

The probability density function for the t distribution is

$$
P(x, df) = \frac{\Gamma(\frac{df+1}{2})}{\sqrt{\pi df}
\Gamma(\frac{df}{2})}\Bigl( 1+\frac{x^2}{df} \Bigr)^{-(df+1)/2}

$$

The t test is based on an assumption that the data come from a
Normal distribution. The t test provides a way to test whether
the sample mean (that is the mean calculated from the data) is
a good estimate of the true mean.

The derivation of the t-distribution was first published in
1908 by William Gosset while working for the Guinness Brewery
in Dublin. Due to proprietary issues, he had to publish under
a pseudonym, and so he used the name Student.

### References

* <a id='id1'>**[1]**</a> Dalgaard, Peter, “Introductory Statistics With R”, Springer, 2002.
* <a id='id2'>**[2]**</a> Wikipedia, “Student’s t-distribution” [http://en.wikipedia.org/wiki/Student’s_t-distribution](http://en.wikipedia.org/wiki/Student's_t-distribution)

### Examples

From Dalgaard page 83 <sup>[1](#id1)</sup>, suppose the daily energy intake for 11
women in Kj is:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> intake = mt.array([5260., 5470, 5640, 6180, 6390, 6515, 6805, 7515, \
...                    7515, 8230, 8770])
```

Does their energy intake deviate systematically from the recommended
value of 7725 kJ?

We have 10 degrees of freedom, so is the sample mean within 95% of the
recommended value?

```pycon
>>> s = mt.random.standard_t(10, size=100000)
>>> mt.mean(intake).execute()
6753.636363636364
>>> intake.std(ddof=1).execute()
1142.1232221373727
```

Calculate the t statistic, setting the ddof parameter to the unbiased
value so the divisor in the standard deviation will be degrees of
freedom, N-1.

```pycon
>>> t = (mt.mean(intake)-7725)/(intake.std(ddof=1)/mt.sqrt(len(intake)))
>>> import matplotlib.pyplot as plt
>>> h = plt.hist(s.execute(), bins=100, normed=True)
```

For a one-sided t-test, how far out in the distribution does the t
statistic appear?

```pycon
>>> (mt.sum(s<t) / float(len(s))).execute()
0.0090699999999999999  #random
```

So the p-value is about 0.009, which says the null hypothesis has a
probability of about 99% of being true.
