# maxframe.tensor.random.randn

### maxframe.tensor.random.randn(\*dn, \*\*kw)

Return a sample (or samples) from the “standard normal” distribution.

If positive, int_like or int-convertible arguments are provided,
randn generates an array of shape `(d0, d1, ..., dn)`, filled
with random floats sampled from a univariate “normal” (Gaussian)
distribution of mean 0 and variance 1 (if any of the $d_i$ are
floats, they are first converted to integers by truncation). A single
float randomly sampled from the distribution is returned if no
argument is provided.

This is a convenience function.  If you want an interface that takes a
tuple as the first argument, use numpy.random.standard_normal instead.

* **Parameters:**
  * **d0** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should be all positive.
    If no argument is given a single Python float is returned.
  * **d1** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should be all positive.
    If no argument is given a single Python float is returned.
  * **...** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should be all positive.
    If no argument is given a single Python float is returned.
  * **dn** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should be all positive.
    If no argument is given a single Python float is returned.
* **Returns:**
  **Z** – A `(d0, d1, ..., dn)`-shaped array of floating-point samples from
  the standard normal distribution, or a single such float if
  no parameters were supplied.
* **Return type:**
  Tensor or [float](https://docs.python.org/3/library/functions.html#float)

#### SEE ALSO
`random.standard_normal`
: Similar, but takes a tuple as its argument.

### Notes

For random samples from $N(\mu, \sigma^2)$, use:

`sigma * mt.random.randn(...) + mu`

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.randn().execute()
2.1923875335537315 #random
```

Two-by-four tensor of samples from N(3, 6.25):

```pycon
>>> (2.5 * mt.random.randn(2, 4) + 3).execute()
array([[-4.49401501,  4.00950034, -1.81814867,  7.29718677],  #random
       [ 0.39924804,  4.68456316,  4.99394529,  4.84057254]]) #random
```
