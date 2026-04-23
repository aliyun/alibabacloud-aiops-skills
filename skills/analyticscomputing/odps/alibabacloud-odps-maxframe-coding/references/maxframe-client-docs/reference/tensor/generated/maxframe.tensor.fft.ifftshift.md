# maxframe.tensor.fft.ifftshift

### maxframe.tensor.fft.ifftshift(x, axes=None)

The inverse of fftshift. Although identical for even-length x, the
functions differ by one sample for odd-length x.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **axes** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *shape tuple* *,* *optional*) – Axes over which to calculate.  Defaults to None, which shifts all axes.
* **Returns:**
  **y** – The shifted tensor.
* **Return type:**
  Tensor

#### SEE ALSO
[`fftshift`](maxframe.tensor.fft.fftshift.md#maxframe.tensor.fft.fftshift)
: Shift zero-frequency component to the center of the spectrum.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> freqs = mt.fft.fftfreq(9, d=1./9).reshape(3, 3)
>>> freqs.execute()
array([[ 0.,  1.,  2.],
       [ 3.,  4., -4.],
       [-3., -2., -1.]])
>>> mt.fft.ifftshift(mt.fft.fftshift(freqs)).execute()
array([[ 0.,  1.,  2.],
       [ 3.,  4., -4.],
       [-3., -2., -1.]])
```
