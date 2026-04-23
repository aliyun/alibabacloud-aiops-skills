# maxframe.tensor.fft.rfft

### maxframe.tensor.fft.rfft(a, n=None, axis=-1, norm=None)

Compute the one-dimensional discrete Fourier Transform for real input.

This function computes the one-dimensional *n*-point discrete Fourier
Transform (DFT) of a real-valued array by means of an efficient algorithm
called the Fast Fourier Transform (FFT).

* **Parameters:**
  * **a** (*array_like*) – Input tensor
  * **n** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of points along transformation axis in the input to use.
    If n is smaller than the length of the input, the input is cropped.
    If it is larger, the input is padded with zeros. If n is not given,
    the length of the input along the axis specified by axis is used.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Axis over which to compute the FFT. If not given, the last axis is
    used.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The truncated or zero-padded input, transformed along the axis
  indicated by axis, or the last one if axis is not specified.
  If n is even, the length of the transformed axis is `(n/2)+1`.
  If n is odd, the length is `(n+1)/2`.
* **Return type:**
  complex Tensor
* **Raises:**
  [**IndexError**](https://docs.python.org/3/library/exceptions.html#IndexError) – If axis is larger than the last axis of a.

#### SEE ALSO
`mt.fft`
: For definition of the DFT and conventions used.

[`irfft`](maxframe.tensor.fft.irfft.md#maxframe.tensor.fft.irfft)
: The inverse of rfft.

[`fft`](maxframe.tensor.fft.fft.md#maxframe.tensor.fft.fft)
: The one-dimensional FFT of general (complex) input.

[`fftn`](maxframe.tensor.fft.fftn.md#maxframe.tensor.fft.fftn)
: The *n*-dimensional FFT.

[`rfftn`](maxframe.tensor.fft.rfftn.md#maxframe.tensor.fft.rfftn)
: The *n*-dimensional FFT of real input.

### Notes

When the DFT is computed for purely real input, the output is
Hermitian-symmetric, i.e. the negative frequency terms are just the complex
conjugates of the corresponding positive-frequency terms, and the
negative-frequency terms are therefore redundant.  This function does not
compute the negative frequency terms, and the length of the transformed
axis of the output is therefore `n//2 + 1`.

When `A = rfft(a)` and fs is the sampling frequency, `A[0]` contains
the zero-frequency term 0\*fs, which is real due to Hermitian symmetry.

If n is even, `A[-1]` contains the term representing both positive
and negative Nyquist frequency (+fs/2 and -fs/2), and must also be purely
real. If n is odd, there is no term at fs/2; `A[-1]` contains
the largest positive frequency (fs/2\*(n-1)/n), and is complex in the
general case.

If the input a contains an imaginary part, it is silently discarded.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.fft.fft([0, 1, 0, 0]).execute()
array([ 1.+0.j,  0.-1.j, -1.+0.j,  0.+1.j])
>>> mt.fft.rfft([0, 1, 0, 0]).execute()
array([ 1.+0.j,  0.-1.j, -1.+0.j])
```

Notice how the final element of the fft output is the complex conjugate
of the second element, for real input. For rfft, this symmetry is
exploited to compute only the non-negative frequency terms.
