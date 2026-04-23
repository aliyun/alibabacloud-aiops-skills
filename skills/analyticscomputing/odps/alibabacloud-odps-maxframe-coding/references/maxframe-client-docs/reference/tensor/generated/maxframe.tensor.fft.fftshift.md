# maxframe.tensor.fft.fftshift

### maxframe.tensor.fft.fftshift(x, axes=None)

Shift the zero-frequency component to the center of the spectrum.

This function swaps half-spaces for all axes listed (defaults to all).
Note that `y[0]` is the Nyquist component only if `len(x)` is even.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **axes** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *shape tuple* *,* *optional*) – Axes over which to shift.  Default is None, which shifts all axes.
* **Returns:**
  **y** – The shifted tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`ifftshift`](maxframe.tensor.fft.ifftshift.md#maxframe.tensor.fft.ifftshift)
: The inverse of fftshift.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> freqs = mt.fft.fftfreq(10, 0.1)
>>> freqs.execute()
array([ 0.,  1.,  2.,  3.,  4., -5., -4., -3., -2., -1.])
>>> mt.fft.fftshift(freqs).execute()
array([-5., -4., -3., -2., -1.,  0.,  1.,  2.,  3.,  4.])
```

Shift the zero-frequency component only along the second axis:

```pycon
>>> freqs = mt.fft.fftfreq(9, d=1./9).reshape(3, 3)
>>> freqs.execute()
array([[ 0.,  1.,  2.],
       [ 3.,  4., -4.],
       [-3., -2., -1.]])
>>> mt.fft.fftshift(freqs, axes=(1,)).execute()
array([[ 2.,  0.,  1.],
       [-4.,  3.,  4.],
       [-1., -3., -2.]])
```
