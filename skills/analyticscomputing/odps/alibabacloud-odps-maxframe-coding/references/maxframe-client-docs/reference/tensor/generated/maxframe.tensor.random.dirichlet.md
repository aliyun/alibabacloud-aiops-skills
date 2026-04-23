# maxframe.tensor.random.dirichlet

### maxframe.tensor.random.dirichlet(alpha, size=None, chunk_size=None, gpu=None, dtype=None)

Draw samples from the Dirichlet distribution.

Draw size samples of dimension k from a Dirichlet distribution. A
Dirichlet-distributed random variable can be seen as a multivariate
generalization of a Beta distribution. Dirichlet pdf is the conjugate
prior of a multinomial in Bayesian inference.

* **Parameters:**
  * **alpha** (*array*) – Parameter of the distribution (k dimension for sample of
    dimension k).
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **dtype** (*data-type* *,* *optional*) – Data-type of the returned tensor.
* **Returns:**
  **samples** – The drawn samples, of shape (size, alpha.ndim).
* **Return type:**
  Tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If any value in alpha is less than or equal to zero

### Notes

$$
X \approx \prod_{i=1}^{k}{x^{\alpha_i-1}_i}

$$

Uses the following property for computation: for each dimension,
draw a random sample y_i from a standard gamma generator of shape
alpha_i, then
$X = \frac{1}{\sum_{i=1}^k{y_i}} (y_1, \ldots, y_n)$ is
Dirichlet distributed.

### References

* <a id='id1'>**[1]**</a> David McKay, “Information Theory, Inference and Learning Algorithms,” chapter 23, [http://www.inference.phy.cam.ac.uk/mackay/](http://www.inference.phy.cam.ac.uk/mackay/)
* <a id='id2'>**[2]**</a> Wikipedia, “Dirichlet distribution”, [http://en.wikipedia.org/wiki/Dirichlet_distribution](http://en.wikipedia.org/wiki/Dirichlet_distribution)

### Examples

Taking an example cited in Wikipedia, this distribution can be used if
one wanted to cut strings (each of initial length 1.0) into K pieces
with different lengths, where each piece had, on average, a designated
average length, but allowing some variation in the relative sizes of
the pieces.

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> s = mt.random.dirichlet((10, 5, 3), 20).transpose()
```

```pycon
>>> import matplotlib.pyplot as plt
```

```pycon
>>> plt.barh(range(20), s[0].execute())
>>> plt.barh(range(20), s[1].execute(), left=s[0].execute(), color='g')
>>> plt.barh(range(20), s[2].execute(), left=(s[0]+s[1]).execute(), color='r')
>>> plt.title("Lengths of Strings")
```
