# maxframe.tensor.fft.hfft

### maxframe.tensor.fft.hfft(a, n=None, axis=-1, norm=None)

Compute the FFT of a signal that has Hermitian symmetry, i.e., a real
spectrum.

* **Parameters:**
  * **a** (*array_like*) – The input tensor.
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Length of the transformed axis of the output. For n output
    points, `n//2 + 1` input points are necessary.  If the input is
    longer than this, it is cropped.  If it is shorter than this, it is
    padded with zeros.  If n is not given, it is determined from the
    length of the input along the axis specified by axis.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis over which to compute the FFT. If not given, the last
    axis is used.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axis
  indicated by axis, or the last one if axis is not specified.
  The length of the transformed axis is n, or, if n is not given,
  `2*m - 2` where `m` is the length of the transformed axis of
  the input. To get an odd number of output points, n must be
  specified, for instance as `2*m - 1` in the typical case,
* **Return type:**
  Tensor
* **Raises:**
  [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If axis is larger than the last axis of a.

#### SEE ALSO
[`rfft`](maxframe.tensor.fft.rfft.md#maxframe.tensor.fft.rfft)
: Compute the one-dimensional FFT for real input.

[`ihfft`](maxframe.tensor.fft.ihfft.md#maxframe.tensor.fft.ihfft)
: The inverse of hfft.

### Notes

hfft/ihfft are a pair analogous to rfft/irfft, but for the
opposite case: here the signal has Hermitian symmetry in the time
domain and is real in the frequency domain. So here it’s hfft for
which you must supply the length of the result if it is to be odd.

* even: `ihfft(hfft(a, 2*len(a) - 2) == a`, within roundoff error,
* odd: `ihfft(hfft(a, 2*len(a) - 1) == a`, within roundoff error.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> signal = mt.array([1, 2, 3, 4, 3, 2])
>>> mt.fft.fft(signal).execute()
array([ 15.+0.j,  -4.+0.j,   0.+0.j,  -1.-0.j,   0.+0.j,  -4.+0.j])
>>> mt.fft.hfft(signal[:4]).execute() # Input first half of signal
array([ 15.,  -4.,   0.,  -1.,   0.,  -4.])
>>> mt.fft.hfft(signal, 6).execute()  # Input entire signal and truncate
array([ 15.,  -4.,   0.,  -1.,   0.,  -4.])
```

```pycon
>>> signal = mt.array([[1, 1.j], [-1.j, 2]])
>>> (mt.conj(signal.T) - signal).execute()   # check Hermitian symmetry
array([[ 0.-0.j,  0.+0.j],
       [ 0.+0.j,  0.-0.j]])
>>> freq_spectrum = mt.fft.hfft(signal)
>>> freq_spectrum.execute()
array([[ 1.,  1.],
       [ 2., -2.]])
```
