# maxframe.tensor.fft.irfft

### maxframe.tensor.fft.irfft(a, n=None, axis=-1, norm=None)

Compute the inverse of the n-point DFT for real input.

This function computes the inverse of the one-dimensional *n*-point
discrete Fourier Transform of real input computed by rfft.
In other words, `irfft(rfft(a), len(a)) == a` to within numerical
accuracy. (See Notes below for why `len(a)` is necessary here.)

The input is expected to be in the form returned by rfft, i.e. the
real zero-frequency term followed by the complex positive frequency terms
in order of increasing frequency.  Since the discrete Fourier Transform of
real input is Hermitian-symmetric, the negative frequency terms are taken
to be the complex conjugates of the corresponding positive frequency terms.

* **Parameters:**
  * **a** (*array_like*) – The input tensor.
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Length of the transformed axis of the output.
    For n output points, `n//2+1` input points are necessary.  If the
    input is longer than this, it is cropped.  If it is shorter than this,
    it is padded with zeros.  If n is not given, it is determined from
    the length of the input along the axis specified by axis.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis over which to compute the inverse FFT. If not given, the last
    axis is used.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axis
  indicated by axis, or the last one if axis is not specified.
  The length of the transformed axis is n, or, if n is not given,
  `2*(m-1)` where `m` is the length of the transformed axis of the
  input. To get an odd number of output points, n must be specified.
* **Return type:**
  Tensor
* **Raises:**
  [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If axis is larger than the last axis of a.

#### SEE ALSO
`mt.fft`
: For definition of the DFT and conventions used.

[`rfft`](maxframe.tensor.fft.rfft.md#maxframe.tensor.fft.rfft)
: The one-dimensional FFT of real input, of which irfft is inverse.

[`fft`](maxframe.tensor.fft.fft.md#maxframe.tensor.fft.fft)
: The one-dimensional FFT.

[`irfft2`](maxframe.tensor.fft.irfft2.md#maxframe.tensor.fft.irfft2)
: The inverse of the two-dimensional FFT of real input.

[`irfftn`](maxframe.tensor.fft.irfftn.md#maxframe.tensor.fft.irfftn)
: The inverse of the *n*-dimensional FFT of real input.

### Notes

Returns the real valued n-point inverse discrete Fourier transform
of a, where a contains the non-negative frequency terms of a
Hermitian-symmetric sequence. n is the length of the result, not the
input.

If you specify an n such that a must be zero-padded or truncated, the
extra/removed values will be added/removed at high frequencies. One can
thus resample a series to m points via Fourier interpolation by:
`a_resamp = irfft(rfft(a), m)`.

### Examples

```pycon
>>> import maxframe.tenosr as mt
```

```pycon
>>> mt.fft.ifft([1, -1j, -1, 1j]).execute()
array([ 0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j])
>>> mt.fft.irfft([1, -1j, -1]).execute()
array([ 0.,  1.,  0.,  0.])
```

Notice how the last term in the input to the ordinary ifft is the
complex conjugate of the second term, and the output has zero imaginary
part everywhere.  When calling irfft, the negative frequencies are not
specified, and the output array is purely real.
