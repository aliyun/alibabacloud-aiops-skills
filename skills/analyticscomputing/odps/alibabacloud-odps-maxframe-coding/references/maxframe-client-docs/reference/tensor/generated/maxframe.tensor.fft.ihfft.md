# maxframe.tensor.fft.ihfft

### maxframe.tensor.fft.ihfft(a, n=None, axis=-1, norm=None)

Compute the inverse FFT of a signal that has Hermitian symmetry.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Length of the inverse FFT, the number of points along
    transformation axis in the input to use.  If n is smaller than
    the length of the input, the input is cropped.  If it is larger,
    the input is padded with zeros. If n is not given, the length of
    the input along the axis specified by axis is used.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis over which to compute the inverse FFT. If not given, the last
    axis is used.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see numpy.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axis
  indicated by axis, or the last one if axis is not specified.
  The length of the transformed axis is `n//2 + 1`.
* **Return type:**
  complex Tensor

#### SEE ALSO
[`hfft`](maxframe.tensor.fft.hfft.md#maxframe.tensor.fft.hfft), [`irfft`](maxframe.tensor.fft.irfft.md#maxframe.tensor.fft.irfft)

### Notes

hfft/ihfft are a pair analogous to rfft/irfft, but for the
opposite case: here the signal has Hermitian symmetry in the time
domain and is real in the frequency domain. So here it’s hfft for
which you must supply the length of the result if it is to be odd:

* even: `ihfft(hfft(a, 2*len(a) - 2) == a`, within roundoff error,
* odd: `ihfft(hfft(a, 2*len(a) - 1) == a`, within roundoff error.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> spectrum = mt.array([ 15, -4, 0, -1, 0, -4])
>>> mt.fft.ifft(spectrum).execute()
array([ 1.+0.j,  2.-0.j,  3.+0.j,  4.+0.j,  3.+0.j,  2.-0.j])
>>> mt.fft.ihfft(spectrum).execute()
array([ 1.-0.j,  2.-0.j,  3.-0.j,  4.-0.j])
```
