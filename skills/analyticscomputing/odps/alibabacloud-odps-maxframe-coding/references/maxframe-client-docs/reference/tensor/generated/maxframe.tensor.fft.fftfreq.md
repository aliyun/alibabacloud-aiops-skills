# maxframe.tensor.fft.fftfreq

### maxframe.tensor.fft.fftfreq(n, d=1.0, gpu=None, chunk_size=None)

Return the Discrete Fourier Transform sample frequencies.

The returned float tensor f contains the frequency bin centers in cycles
per unit of the sample spacing (with zero at the start).  For instance, if
the sample spacing is in seconds, then the frequency unit is cycles/second.

Given a window length n and a sample spacing d:

```default
f = [0, 1, ...,   n/2-1,     -n/2, ..., -1] / (d*n)   if n is even
f = [0, 1, ..., (n-1)/2, -(n-1)/2, ..., -1] / (d*n)   if n is odd
```

* **Parameters:**
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Window length.
  * **d** (*scalar* *,* *optional*) – Sample spacing (inverse of the sampling rate). Defaults to 1.
  * **gpu** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Allocate the tensor on GPU if True, False as default
  * **chunk_size** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ints* *,* *optional*) – Desired chunk size on each dimension
* **Returns:**
  **f** – Array of length n containing the sample frequencies.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> signal = mt.array([-2, 8, 6, 4, 1, 0, 3, 5], dtype=float)
>>> fourier = mt.fft.fft(signal)
>>> n = signal.size
>>> timestep = 0.1
>>> freq = mt.fft.fftfreq(n, d=timestep)
>>> freq.execute()
array([ 0.  ,  1.25,  2.5 ,  3.75, -5.  , -3.75, -2.5 , -1.25])
```
