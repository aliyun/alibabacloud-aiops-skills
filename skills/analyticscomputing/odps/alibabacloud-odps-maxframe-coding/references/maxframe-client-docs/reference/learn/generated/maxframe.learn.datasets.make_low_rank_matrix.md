# maxframe.learn.datasets.make_low_rank_matrix

### maxframe.learn.datasets.make_low_rank_matrix(n_samples=100, n_features=100, effective_rank=10, tail_strength=0.5, random_state=None, chunk_size=None)

Generate a mostly low rank matrix with bell-shaped singular values

Most of the variance can be explained by a bell-shaped curve of width
effective_rank: the low rank part of the singular values profile is:

```default
(1 - tail_strength) * exp(-1.0 * (i / effective_rank) ** 2)
```

The remaining singular values’ tail is fat, decreasing as:

```default
tail_strength * exp(-0.1 * i / effective_rank).
```

The low rank part of the profile can be considered the structured
signal part of the data while the tail can be considered the noisy
part of the data that cannot be summarized by a low number of linear
components (singular vectors).

This kind of singular profiles is often seen in practice, for instance:
: - gray level pictures of faces
  - TF-IDF vectors of text documents crawled from the web

Read more in the User Guide.

* **Parameters:**
  * **n_samples** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=100* *)*) – The number of samples.
  * **n_features** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=100* *)*) – The number of features.
  * **effective_rank** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional* *(**default=10* *)*) – The approximate number of singular vectors required to explain most of
    the data by linear combinations.
  * **tail_strength** (*float between 0.0 and 1.0* *,* *optional* *(**default=0.5* *)*) – The relative importance of the fat noisy tail of the singular values
    profile.
  * **random_state** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *RandomState instance* *or* *None* *(**default* *)*) – Determines random number generation for dataset creation. Pass an int
    for reproducible output across multiple function calls.
    See Glossary.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **X** – The matrix.
* **Return type:**
  array of shape [n_samples, n_features]
