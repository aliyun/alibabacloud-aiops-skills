# maxframe.tensor.bincount

### maxframe.tensor.bincount(x, weights=None, minlength=0, chunk_size_limit=None)

Count number of occurrences of each value in array of non-negative ints.

The number of bins (of size 1) is one larger than the largest value in
x. If minlength is specified, there will be at least this number
of bins in the output array (though it will be longer if necessary,
depending on the contents of x).
Each bin gives the number of occurrences of its index value in x.
If weights is specified the input array is weighted by it, i.e. if a
value `n` is found at position `i`, `out[n] += weight[i]` instead
of `out[n] += 1`.

* **Parameters:**
  * **x** (*tensor* *or* *array_like* *,* *1 dimension* *,* *nonnegative ints*) – Input array.
  * **weights** (*tensor* *or* *array_like* *,* *optional*) – Weights, array of the same shape as x.
  * **minlength** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – A minimum number of bins for the output array.
* **Returns:**
  **out** – The result of binning the input array.
  The length of out is equal to `np.amax(x)+1`.
* **Return type:**
  tensor of ints
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If the input is not 1-dimensional, or contains elements with negative
        values, or if minlength is negative.
  * [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If the type of the input is float or complex.

#### SEE ALSO
[`histogram`](maxframe.tensor.histogram.md#maxframe.tensor.histogram), [`digitize`](maxframe.tensor.digitize.md#maxframe.tensor.digitize), [`unique`](maxframe.tensor.unique.md#maxframe.tensor.unique)

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> mt.bincount(mt.arange(5)).execute()
array([1, 1, 1, 1, 1])
>>> mt.bincount(mt.tensor([0, 1, 1, 3, 2, 1, 7])).execute()
array([1, 3, 1, 1, 0, 0, 0, 1])
```

The input array needs to be of integer dtype, otherwise a
TypeError is raised:

```pycon
>>> mt.bincount(mt.arange(5, dtype=float)).execute()
Traceback (most recent call last):
  ....execute()
TypeError: Cannot cast array data from dtype('float64') to dtype('int64')
according to the rule 'safe'
```

A possible use of `bincount` is to perform sums over
variable-size chunks of an array, using the `weights` keyword.

```pycon
>>> w = mt.array([0.3, 0.5, 0.2, 0.7, 1., -0.6]) # weights
>>> x = mt.array([0, 1, 1, 2, 2, 2])
>>> mt.bincount(x, weights=w).execute()
array([ 0.3,  0.7,  1.1])
```
