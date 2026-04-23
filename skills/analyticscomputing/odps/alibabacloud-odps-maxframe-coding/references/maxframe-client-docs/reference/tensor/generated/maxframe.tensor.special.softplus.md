# maxframe.tensor.special.softplus

### maxframe.tensor.special.softplus(x, \*\*kwargs)

Compute the softplus function element-wise.

The softplus function is defined as: `softplus(x) = log(1 + exp(x))`.
It is a smooth approximation of the rectifier function (ReLU).

* **Parameters:**
  * **x** (*array_like*) – Input value.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html).
* **Returns:**
  **softplus** – Logarithm of `exp(0) + exp(x)`.
* **Return type:**
  ndarray

### Examples

```pycon
>>> from maxframe.tensor import special
```

```pycon
>>> special.softplus(0).to_numpy()
0.6931471805599453
```

```pycon
>>> special.softplus([-1, 0, 1]).to_numpy()
array([0.31326169, 0.69314718, 1.31326169])
```
