# maxframe.tensor.fft.irfft2

### maxframe.tensor.fft.irfft2(a, s=None, axes=(-2, -1), norm=None)

Compute the 2-dimensional inverse FFT of a real array.

* **Parameters:**
  * **a** (*array_like*) – The input tensor
  * **s** (*sequence* *of* *ints* *,* *optional*) – Shape of the inverse FFT.
  * **axes** (*sequence* *of* *ints* *,* *optional*) – The axes over which to compute the inverse fft.
    Default is the last two axes.
  * **norm** ( *{None* *,*  *"ortho"}* *,* *optional*) – Normalization mode (see mt.fft). Default is None.
* **Returns:**
  **out** – The result of the inverse real 2-D FFT.
* **Return type:**
  Tensor

#### SEE ALSO
[`irfftn`](maxframe.tensor.fft.irfftn.md#maxframe.tensor.fft.irfftn)
: Compute the inverse of the N-dimensional FFT of real input.

### Notes

This is really irfftn with different defaults.
For more details see irfftn.
