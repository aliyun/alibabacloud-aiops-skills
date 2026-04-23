# maxframe.tensor.special.softmax

### maxframe.tensor.special.softmax(x, axis=None)

Compute the softmax function.
The softmax function transforms each element of a collection by
computing the exponential of each element divided by the sum of the
exponentials of all the elements. That is, if x is a one-dimensional
numpy array:

```default
softmax(x) = np.exp(x)/sum(np.exp(x))
```

* **Parameters:**
  * **x** (*array_like*) – Input array.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Axis to compute values along. Default is None and softmax will be
    computed over the entire array x.
* **Returns:**
  **s** – An array the same shape as x. The result will sum to 1 along the
  specified axis.
* **Return type:**
  ndarray

### Notes

The formula for the softmax function $\sigma(x)$ for a vector
$x = \{x_0, x_1, ..., x_{n-1}\}$ is

$$
\sigma(x)_j = \frac{e^{x_j}}{\sum_k e^{x_k}}

$$

The softmax function is the gradient of logsumexp.

The implementation uses shifting to avoid overflow. See <sup>[1](#id2)</sup> for more
details.

### References

* <a id='id2'>**[1]**</a> P. Blanchard, D.J. Higham, N.J. Higham, “Accurately computing the log-sum-exp and softmax functions”, IMA Journal of Numerical Analysis, Vol.41(4),   ``` :doi:`10.1093/imanum/draa038` ```  .

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> from maxframe.tensor.special import softmax
```

```pycon
>>> x = mt.array([[1, 0.5, 0.2, 3],
...               [1,  -1,   7, 3],
...               [2,  12,  13, 3]])
...
```

Compute the softmax transformation over the entire array.

```pycon
>>> m = softmax(x)
>>> m.to_numpy()
array([[  4.48309e-06,   2.71913e-06,   2.01438e-06,   3.31258e-05],
       [  4.48309e-06,   6.06720e-07,   1.80861e-03,   3.31258e-05],
       [  1.21863e-05,   2.68421e-01,   7.29644e-01,   3.31258e-05]])
```

```pycon
>>> m.sum().to_numpy()
1.0
```

Compute the softmax transformation along the first axis (i.e., the
columns).

```pycon
>>> m = softmax(x, axis=0)
>>> m.to_numpy()
array([[  2.11942e-01,   1.01300e-05,   2.75394e-06,   3.33333e-01],
       [  2.11942e-01,   2.26030e-06,   2.47262e-03,   3.33333e-01],
       [  5.76117e-01,   9.99988e-01,   9.97525e-01,   3.33333e-01]])
>>> m.sum(axis=0).to_numpy()
array([ 1.,  1.,  1.,  1.])
```

Compute the softmax transformation along the second axis (i.e., the rows).

```pycon
>>> m = softmax(x, axis=1)
>>> m.to_numpy()
array([[  1.05877e-01,   6.42177e-02,   4.75736e-02,   7.82332e-01],
       [  2.42746e-03,   3.28521e-04,   9.79307e-01,   1.79366e-02],
       [  1.22094e-05,   2.68929e-01,   7.31025e-01,   3.31885e-05]])
>>> m.sum(axis=1).to_numpy()
array([ 1.,  1.,  1.])
```
