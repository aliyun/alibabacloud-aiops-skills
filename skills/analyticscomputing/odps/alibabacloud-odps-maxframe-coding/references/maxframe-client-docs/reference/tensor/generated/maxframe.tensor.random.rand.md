# maxframe.tensor.random.rand

### maxframe.tensor.random.rand(\*dn, \*\*kw)

Random values in a given shape.

Create a tensor of the given shape and populate it with
random samples from a uniform distributionc
over `[0, 1)`.

* **Parameters:**
  * **d0** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should all be positive.
    If no argument is given a single Python float is returned.
  * **d1** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should all be positive.
    If no argument is given a single Python float is returned.
  * **...** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should all be positive.
    If no argument is given a single Python float is returned.
  * **dn** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – The dimensions of the returned tensor, should all be positive.
    If no argument is given a single Python float is returned.
* **Returns:**
  **out** – Random values.
* **Return type:**
  Tensor, shape `(d0, d1, ..., dn)`

#### SEE ALSO
[`random`](maxframe.tensor.random.random.md#maxframe.tensor.random.random)

### Notes

This is a convenience function. If you want an interface that
takes a shape-tuple as the first argument, refer to
mt.random.random_sample .

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.random.rand(3, 2).execute()
array([[ 0.14022471,  0.96360618],  #random
       [ 0.37601032,  0.25528411],  #random
       [ 0.49313049,  0.94909878]]) #random
```
