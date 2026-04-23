# maxframe.tensor.random.choice

### maxframe.tensor.random.choice(a, size=None, replace=True, p=None, chunk_size=None, gpu=None)

Generates a random sample from a given 1-D array

* **Parameters:**
  * **a** (*1-D array-like* *or* [*int*](https://docs.python.org/3/library/functions.html#int)) – If a tensor, a random sample is generated from its elements.
    If an int, the random sample is generated as if a were mt.arange(a)
  * **size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Output shape.  If the given shape is, e.g., `(m, n, k)`, then
    `m * n * k` samples are drawn.  Default is None, in which case a
    single value is returned.
  * **replace** (*boolean* *,* *optional*) – Whether the sample is with or without replacement
  * **p** (*1-D array-like* *,* *optional*) – The probabilities associated with each entry in a.
    If not given the sample assumes a uniform distribution over all
    entries in a.
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
* **Returns:**
  **samples** – The generated random samples
* **Return type:**
  single item or tensor
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If a is an int and less than zero, if a or p are not 1-dimensional,
      if a is an array-like of size 0, if p is not a vector of
      probabilities, if a and p have different lengths, or if
      replace=False and the sample size is greater than the population
      size

#### SEE ALSO
[`randint`](maxframe.tensor.random.randint.md#maxframe.tensor.random.randint), `shuffle`, [`permutation`](maxframe.tensor.random.permutation.md#maxframe.tensor.random.permutation)

### Examples

Generate a uniform random sample from mt.arange(5) of size 3:

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.choice(5, 3).execute()
array([0, 3, 4])
>>> #This is equivalent to mt.random.randint(0,5,3)
```

Generate a non-uniform random sample from np.arange(5) of size 3:

```pycon
>>> mt.random.choice(5, 3, p=[0.1, 0, 0.3, 0.6, 0]).execute()
array([3, 3, 0])
```

Generate a uniform random sample from mt.arange(5) of size 3 without
replacement:

```pycon
>>> mt.random.choice(5, 3, replace=False).execute()
array([3,1,0])
>>> #This is equivalent to np.random.permutation(np.arange(5))[:3]
```

Generate a non-uniform random sample from mt.arange(5) of size
3 without replacement:

```pycon
>>> mt.random.choice(5, 3, replace=False, p=[0.1, 0, 0.3, 0.6, 0]).execute()
array([2, 3, 0])
```

Any of the above can be repeated with an arbitrary array-like
instead of just integers. For instance:

```pycon
>>> aa_milne_arr = ['pooh', 'rabbit', 'piglet', 'Christopher']
>>> np.random.choice(aa_milne_arr, 5, p=[0.5, 0.1, 0.1, 0.3])
array(['pooh', 'pooh', 'pooh', 'Christopher', 'piglet'],
      dtype='|S11')
```
