# maxframe.tensor.fft.rfftfreq

### maxframe.tensor.fft.rfftfreq(n, d=1.0, gpu=None, chunk_size=None)

Return the Discrete Fourier Transform sample frequencies
(for usage with rfft, irfft).

The returned float tensor f contains the frequency bin centers in cycles
per unit of the sample spacing (with zero at the start).  For instance, if
the sample spacing is in seconds, then the frequency unit is cycles/second.

Given a window length n and a sample spacing d:

```default
f = [0, 1, ...,     n/2-1,     n/2] / (d*n)   if n is even
f = [0, 1, ..., (n-1)/2-1, (n-1)/2] / (d*n)   if n is odd
```

Unlike fftfreq (but like scipy.fftpack.rfftfreq)
the Nyquist frequency component is considered to be positive.

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Window length.
  * **d** (*scalar* *,* *optional*) – Sample spacing (inverse of the sampling rate). Defaults to 1.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **f** – Tensor of length `n//2 + 1` containing the sample frequencies.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> signal = mt.array([-2, 8, 6, 4, 1, 0, 3, 5, -3, 4], dtype=float)
>>> fourier = mt.fft.rfft(signal)
>>> n = signal.size
>>> sample_rate = 100
>>> freq = mt.fft.fftfreq(n, d=1./sample_rate)
>>> freq.execute()
array([  0.,  10.,  20.,  30.,  40., -50., -40., -30., -20., -10.])
>>> freq = mt.fft.rfftfreq(n, d=1./sample_rate)
>>> freq.execute()
array([  0.,  10.,  20.,  30.,  40.,  50.])
```
