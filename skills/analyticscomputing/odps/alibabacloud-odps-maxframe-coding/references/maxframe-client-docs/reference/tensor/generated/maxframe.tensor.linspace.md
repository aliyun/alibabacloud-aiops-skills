# maxframe.tensor.linspace

### maxframe.tensor.linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None, gpu=None, chunk_size=None)

Return evenly spaced numbers over a specified interval.

Returns num evenly spaced samples, calculated over the
interval [start, stop].

The endpoint of the interval can optionally be excluded.

* **Parameters:**
  * **start** (*scalar*) – The starting value of the sequence.
  * **stop** (*scalar*) – The end value of the sequence, unless endpoint is set to False.
    In that case, the sequence consists of all but the last of `num + 1`
    evenly spaced samples, so that stop is excluded.  Note that the step
    size changes when endpoint is False.
  * **num** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of samples to generate. Default is 50. Must be non-negative.
  * **endpoint** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, stop is the last sample. Otherwise, it is not included.
    Default is True.
  * **retstep** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, return (samples, step), where step is the spacing
    between samples.
  * **dtype** (*dtype* *,* *optional*) – The type of the output tensor.  If dtype is not given, infer the data
    type from the other input arguments.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  * **samples** (*Tensor*) – There are num equally spaced samples in the closed interval
    `[start, stop]` or the half-open interval `[start, stop)`
    (depending on whether endpoint is True or False).
  * **step** (*float, optional*) – Only returned if retstep is True

    Size of spacing between samples.

#### SEE ALSO
[`arange`](maxframe.tensor.arange.md#maxframe.tensor.arange)
: Similar to linspace, but uses a step size (instead of the number of samples).

`logspace`
: Samples uniformly distributed in log space.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.linspace(2.0, 3.0, num=5).execute()
array([ 2.  ,  2.25,  2.5 ,  2.75,  3.  ])
>>> mt.linspace(2.0, 3.0, num=5, endpoint=False).execute()
array([ 2. ,  2.2,  2.4,  2.6,  2.8])
>>> mt.linspace(2.0, 3.0, num=5, retstep=True).execute()
(array([ 2.  ,  2.25,  2.5 ,  2.75,  3.  ]), 0.25)
```

Graphical illustration:

```pycon
>>> import matplotlib.pyplot as plt
>>> N = 8
>>> y = mt.zeros(N)
>>> x1 = mt.linspace(0, 10, N, endpoint=True)
>>> x2 = mt.linspace(0, 10, N, endpoint=False)
>>> plt.plot(x1.execute(), y.execute(), 'o')
[<matplotlib.lines.Line2D object at 0x...>]
>>> plt.plot(x2.execute(), y.execute() + 0.5, 'o')
[<matplotlib.lines.Line2D object at 0x...>]
>>> plt.ylim([-0.5, 1])
(-0.5, 1)
>>> plt.show()
```
